"""
Jira Connector Skill v2.0 — Enhanced with:
- Full ADF parsing (tables, panels, code blocks, media)
- Image attachment reading via vision LLM
- PDF text extraction (pymupdf or pypdf fallback)
- Structured content preservation
"""
import io
import base64
import structlog
import time
from typing import Optional
from atlassian import Jira
from core.secret_manager import secret_manager
from core.agent_contracts import QATicketDraft

logger = structlog.get_logger(__name__)


class JiraConnector:
    def __init__(self):
        self.client = Jira(
            url=secret_manager.get("jira_base_url"),
            username=secret_manager.get("jira_email"),
            password=secret_manager.get("jira_token"),
            cloud=True,
        )
        self.project_key = secret_manager.get("jira_project_key")
        self._rate_limit = 0.5
        self._base_url   = secret_manager.get("jira_base_url")

    # ── READ ─────────────────────────────────────────────────────────────

    def get_issue(self, issue_key: str) -> dict:
        try:
            issue = self.client.issue(issue_key)
            logger.info("jira_issue_fetched", key=issue_key)
            return issue
        except Exception as e:
            logger.error("jira_fetch_failed", key=issue_key, error=str(e))
            raise

    def get_story_text(self, issue_key: str, include_attachments: bool = True) -> str:
        issue  = self.get_issue(issue_key)
        fields = issue.get("fields", {})

        summary     = fields.get("summary", "")
        description = self._extract_full_content(fields.get("description", ""))
        ac_field    = fields.get("customfield_10016", "") or ""

        text = f"Story: {summary}\n\nDescription:\n{description}"
        if ac_field:
            text += f"\n\nAcceptance Criteria:\n{ac_field}"

        if include_attachments:
            att_text = self._read_attachments(issue_key, fields)
            if att_text:
                text += f"\n\nAttachments:\n{att_text}"

        return text

    def get_stories_for_epic(self, epic_key: str) -> list[dict]:
        jql = f'"Epic Link" = {epic_key} ORDER BY priority DESC'
        try:
            result = self.client.jql(jql, limit=50)
            issues = result.get("issues", [])
            logger.info("jira_epic_stories", epic=epic_key, count=len(issues))
            return issues
        except Exception as e:
            logger.error("jira_epic_fetch_failed", epic=epic_key, error=str(e))
            return []

    # ── ADF PARSING ───────────────────────────────────────────────────────

    def _extract_full_content(self, desc) -> str:
        if not desc:
            return ""
        if isinstance(desc, str):
            return desc
        if isinstance(desc, dict) and desc.get("type") == "doc":
            return self._parse_adf_node(desc)
        return str(desc)

    def _parse_adf_node(self, node: dict, indent: int = 0) -> str:
        t       = node.get("type", "")
        content = node.get("content", [])
        attrs   = node.get("attrs", {})

        if t == "text":
            return node.get("text", "")
        if t in ("doc", "blockquote"):
            return "".join(self._parse_adf_node(c, indent) for c in content)
        if t == "paragraph":
            inner = "".join(self._parse_adf_node(c) for c in content)
            return inner + "\n"
        if t == "heading":
            level = attrs.get("level", 1)
            inner = "".join(self._parse_adf_node(c) for c in content)
            return f"\n{'#' * level} {inner}\n"
        if t == "bulletList":
            items = []
            for item in content:
                txt = "".join(
                    self._parse_adf_node(c, indent)
                    for c in item.get("content", [])
                ).strip()
                items.append(f"{'  ' * indent}• {txt}")
            return "\n".join(items) + "\n"
        if t == "orderedList":
            items = []
            for i, item in enumerate(content, 1):
                txt = "".join(
                    self._parse_adf_node(c, indent)
                    for c in item.get("content", [])
                ).strip()
                items.append(f"{'  ' * indent}{i}. {txt}")
            return "\n".join(items) + "\n"
        if t == "listItem":
            return "".join(self._parse_adf_node(c, indent) for c in content)
        if t == "table":
            return self._parse_table(content)
        if t == "codeBlock":
            lang  = attrs.get("language", "")
            inner = "".join(self._parse_adf_node(c) for c in content)
            return f"\n```{lang}\n{inner}\n```\n"
        if t == "panel":
            panel_type = attrs.get("panelType", "info")
            inner = "".join(self._parse_adf_node(c, indent) for c in content)
            return f"\n[{panel_type.upper()}]\n{inner}\n"
        if t == "rule":
            return "\n---\n"
        if t == "hardBreak":
            return "\n"
        if t == "mention":
            return f"@{attrs.get('text', 'user')}"
        if t in ("media", "mediaSingle", "mediaGroup"):
            alt = attrs.get("alt", attrs.get("id", "attachment"))
            return f"[Image: {alt}]\n"
        if t == "inlineCard":
            return f"[{attrs.get('url', 'link')}]"
        # fallback
        return "".join(self._parse_adf_node(c, indent) for c in content)

    def _parse_table(self, rows: list) -> str:
        if not rows:
            return ""
        parsed = []
        for row in rows:
            cells = []
            for cell in row.get("content", []):
                txt = "".join(
                    self._parse_adf_node(c)
                    for c in cell.get("content", [])
                ).strip().replace("\n", " ")
                cells.append(txt)
            parsed.append(cells)
        if not parsed:
            return ""
        lines = []
        header = parsed[0]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join(["---"] * len(header)) + " |")
        for row in parsed[1:]:
            while len(row) < len(header):
                row.append("")
            lines.append("| " + " | ".join(row) + " |")
        return "\n" + "\n".join(lines) + "\n"

    # ── ATTACHMENT READING ────────────────────────────────────────────────

    def _read_attachments(self, issue_key: str, fields: dict) -> str:
        attachments = fields.get("attachment", [])
        if not attachments:
            return ""

        results = []
        for att in attachments:
            filename  = att.get("filename", "")
            mime_type = att.get("mimeType", "")
            url       = att.get("content", "")

            logger.info("reading_attachment", filename=filename, type=mime_type)
            try:
                content_bytes = self._download_attachment(url)
                if not content_bytes:
                    continue

                if mime_type.startswith("image/"):
                    text = self._read_image(content_bytes, filename, mime_type)
                elif mime_type == "application/pdf":
                    text = self._read_pdf(content_bytes, filename)
                elif mime_type.startswith("text/"):
                    text = content_bytes.decode("utf-8", errors="ignore")[:3000]
                else:
                    continue

                if text:
                    results.append(f"=== {filename} ===\n{text}")

            except Exception as e:
                logger.warning("attachment_failed", filename=filename, error=str(e))

        return "\n\n".join(results)

    def _download_attachment(self, url: str) -> Optional[bytes]:
        try:
            import requests
            r = requests.get(
                url,
                auth=(
                    secret_manager.get("jira_email"),
                    secret_manager.get("jira_token"),
                ),
                timeout=30,
            )
            if r.status_code == 200:
                return r.content
            logger.warning("download_failed", status=r.status_code)
            return None
        except Exception as e:
            logger.error("download_error", error=str(e))
            return None

    def _read_image(self, image_bytes: bytes, filename: str, mime_type: str) -> str:
        """Analyze image using vision-capable LLM on OpenRouter."""
        try:
            from openai import OpenAI
            b64 = base64.b64encode(image_bytes).decode("utf-8")
            client = OpenAI(
                api_key=secret_manager.get("openrouter_api_key"),
                base_url=secret_manager.get("openrouter_base_url"),
            )
            response = client.chat.completions.create(
                model="openai/gpt-oss-20b:free",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url",
                         "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
                        {"type": "text",
                         "text": (
                             "You are a QA engineer analyzing a UI screenshot or flow diagram "
                             "attached to a Jira story. Describe: "
                             "1) What UI elements or flows are shown, "
                             "2) Any acceptance criteria or test conditions visible, "
                             "3) Edge cases suggested by the design. "
                             "Be specific and technical. Focus on testable behaviors."
                         )}
                    ]
                }],
                max_tokens=800,
            )
            desc = response.choices[0].message.content
            logger.info("image_analyzed", filename=filename)
            return f"[Image Analysis]\n{desc}"
        except Exception as e:
            logger.warning("image_analysis_failed", filename=filename, error=str(e))
            return f"[Image: {filename} — analysis failed: {str(e)[:80]}]"

    def _read_pdf(self, pdf_bytes: bytes, filename: str) -> str:
        """Extract text from PDF. Tries pymupdf first, then pypdf."""
        try:
            import pymupdf
            doc  = pymupdf.open(stream=pdf_bytes, filetype="pdf")
            text = "\n\n".join(
                f"[Page {i+1}]\n{page.get_text()}"
                for i, page in enumerate(doc)
            )
            logger.info("pdf_read_pymupdf", filename=filename, pages=len(doc))
            return text[:5000]
        except ImportError:
            pass
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(pdf_bytes))
            text   = "\n\n".join(
                f"[Page {i+1}]\n{page.extract_text()}"
                for i, page in enumerate(reader.pages)
            )
            logger.info("pdf_read_pypdf_fallback", filename=filename)
            return text[:5000]
        except ImportError:
            pass
        return f"[PDF: {filename} — install: pip install pymupdf]"

    # ── WRITE OPERATIONS ─────────────────────────────────────────────────

    def create_ticket(self, draft: QATicketDraft) -> str:
        time.sleep(self._rate_limit)
        fields = {
            "project":     {"key": self.project_key},
            "summary":     draft.title,
            "issuetype":   {"name": draft.issue_type},
            "priority":    {"name": draft.priority.capitalize()},
            "labels":      draft.labels,
            "description": self._format_description(draft),
        }
        if draft.components:
            fields["components"] = [{"name": c} for c in draft.components]
        try:
            issue = self.client.create_issue(fields=fields)
            key   = issue.get("key", "")
            logger.info("jira_ticket_created", key=key)
            if draft.parent_key:
                self._link_issue(key, draft.parent_key)
            return key
        except Exception as e:
            logger.error("jira_create_failed", error=str(e))
            raise

    def bulk_create(self, drafts: list[QATicketDraft]) -> list[dict]:
        results = []
        for i, draft in enumerate(drafts, 1):
            logger.info("bulk_create_progress", current=i, total=len(drafts))
            try:
                key = self.create_ticket(draft)
                results.append({"key": key, "success": True, "title": draft.title})
            except Exception as e:
                results.append({"key": None, "success": False,
                                "title": draft.title, "error": str(e)})
        return results

    def _link_issue(self, from_key: str, to_key: str):
        try:
            self.client.create_issue_link(
                link_type="relates to",
                inward_issue=from_key,
                outward_issue=to_key,
            )
        except Exception as e:
            logger.warning("jira_link_failed", from_key=from_key,
                           to_key=to_key, error=str(e))

    def _format_description(self, draft: QATicketDraft) -> str:
        parts = []
        if draft.precondition:
            parts.append(f"h3. Precondition\n{draft.precondition}")
        if draft.steps:
            parts.append("h3. Test Steps\n" + "\n".join(f"# {s}" for s in draft.steps))
        if draft.expected:
            parts.append(f"h3. Expected Result\n{draft.expected}")
        if draft.test_data:
            parts.append(f"h3. Test Data\n{draft.test_data}")
        if draft.edge_cases:
            parts.append("h3. Edge Cases\n" + "\n".join(f"* {ec}" for ec in draft.edge_cases))
        parts.append(
            f"----\nGenerated by: {draft.generated_by} | "
            f"Prompt: v{draft.prompt_version} | "
            f"Automation: {'Yes' if draft.automation_candidate else 'No'}"
        )
        return "\n\n".join(parts)

    def _extract_description(self, desc) -> str:
        """Backward compatibility."""
        return self._extract_full_content(desc)


jira_connector = JiraConnector()
