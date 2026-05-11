"""
MCP Jira Client — Full Jira integration for QA framework.
"""
import os
import base64
import httpx
import structlog
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")
logger = structlog.get_logger(__name__)


class JiraClient:
    def __init__(self):
        self.base_url = os.getenv("JIRA_BASE_URL", "")
        self.email    = os.getenv("JIRA_EMAIL", "")
        self.token    = os.getenv("JIRA_TOKEN", "")
        self.project  = os.getenv("JIRA_PROJECT_KEY", "HM")
        auth = base64.b64encode(f"{self.email}:{self.token}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json"
        }

    def _extract_adf_text(self, node, depth=0) -> str:
        """Extract plain text from ADF — handles paragraphs, lists, tables, headings."""
        text = ""
        if not isinstance(node, dict):
            return text

        node_type = node.get("type", "")

        # Text node — just get the text
        if node_type == "text":
            marks = node.get("marks", [])
            t = node.get("text", "")
            # Bold/strong text — keep as is
            return t

        # Heading — add newline + text
        if node_type == "heading":
            level = node.get("attrs", {}).get("level", 1)
            children = "".join(self._extract_adf_text(c, depth) for c in node.get("content", []))
            return f"\n{'#' * level} {children}\n"

        # Paragraph
        if node_type == "paragraph":
            children = "".join(self._extract_adf_text(c, depth) for c in node.get("content", []))
            return children.strip() + "\n" if children.strip() else ""

        # Bullet list item
        if node_type == "listItem":
            children = "".join(self._extract_adf_text(c, depth) for c in node.get("content", []))
            indent = "  " * depth
            return f"{indent}- {children.strip()}\n"

        # Bullet/ordered list
        if node_type in ["bulletList", "orderedList"]:
            children = "".join(self._extract_adf_text(c, depth + 1) for c in node.get("content", []))
            return children + "\n"

        # Table
        if node_type == "table":
            rows = []
            for row in node.get("content", []):
                cells = []
                for cell in row.get("content", []):
                    cell_text = "".join(self._extract_adf_text(c, depth) for c in cell.get("content", []))
                    cells.append(cell_text.strip())
                rows.append(" | ".join(cells))
            return "\n".join(rows) + "\n"

        # Code block
        if node_type == "codeBlock":
            children = "".join(self._extract_adf_text(c, depth) for c in node.get("content", []))
            return f"```\n{children}\n```\n"

        # Panel (info/warning boxes)
        if node_type == "panel":
            children = "".join(self._extract_adf_text(c, depth) for c in node.get("content", []))
            panel_type = node.get("attrs", {}).get("panelType", "info")
            return f"[{panel_type.upper()}] {children}\n"

        # Media/image — note it exists but can't extract pixel content
        if node_type in ["media", "mediaSingle", "mediaGroup"]:
            media_id = node.get("attrs", {}).get("id", "")
            return f"[IMAGE: {media_id}]\n" if media_id else "[IMAGE]\n"

        # Inline card / mention / emoji
        if node_type == "inlineCard":
            url = node.get("attrs", {}).get("url", "")
            return f"[LINK: {url}] "
        if node_type == "mention":
            return f"@{node.get('attrs', {}).get('text', 'user')} "
        if node_type == "emoji":
            return node.get("attrs", {}).get("text", "") + " "

        # Hard break
        if node_type == "hardBreak":
            return "\n"

        # Default — recurse into children
        return "".join(self._extract_adf_text(c, depth) for c in node.get("content", []))

    def get_issue(self, issue_key: str) -> dict:
        with httpx.Client() as client:
            r = client.get(
                f"{self.base_url}/rest/api/3/issue/{issue_key}",
                headers=self.headers
            )
        r.raise_for_status()
        fields = r.json().get("fields", {})

        desc_raw  = fields.get("description", {})
        desc_text = self._extract_adf_text(desc_raw) if isinstance(desc_raw, dict) else str(desc_raw or "")

        ac_list = []
        for line in desc_text.split("\n"):
            line = line.strip().lstrip("-•").strip()
            if line and 15 < len(line) < 300:
                ac_list.append(line)

        subtasks = []
        for st in fields.get("subtasks", [])[:10]:
            st_key     = st.get("key")
            st_summary = st.get("fields", {}).get("summary", "")
            st_status  = st.get("fields", {}).get("status", {}).get("name", "")
            try:
                with httpx.Client() as client:
                    st_r = client.get(
                        f"{self.base_url}/rest/api/3/issue/{st_key}",
                        headers=self.headers
                    )
                st_desc_raw = st_r.json().get("fields", {}).get("description", {})
                st_desc = self._extract_adf_text(st_desc_raw) if isinstance(st_desc_raw, dict) else ""
            except Exception:
                st_desc = ""

            subtasks.append({
                "key": st_key,
                "summary": st_summary,
                "status": st_status,
                "description": st_desc[:300]
            })

        return {
            "key":                  issue_key,
            "summary":              fields.get("summary", ""),
            "status":               fields.get("status", {}).get("name", ""),
            "priority":             fields.get("priority", {}).get("name", ""),
            "issue_type":           fields.get("issuetype", {}).get("name", ""),
            "assignee":             (fields.get("assignee") or {}).get("displayName", "Unassigned"),
            "description":          desc_text.strip(),
            "acceptance_criteria":  ac_list,
            "subtasks":             subtasks,
            "labels":               fields.get("labels", []),
            "sprint":               next(
                (s.get("name") for s in (fields.get("customfield_10020") or [])
                 if s.get("state") == "active"), None
            )
        }

    def get_attachments(self, issue_key: str) -> list:
        """Fetch all attachments from a Jira issue."""
        with httpx.Client() as client:
            r = client.get(
                f"{self.base_url}/rest/api/3/issue/{issue_key}",
                headers=self.headers,
                params={"fields": "attachment"}
            )
        attachments = r.json().get("fields", {}).get("attachment", [])
        return [{
            "id":       a.get("id"),
            "filename": a.get("filename"),
            "mimeType": a.get("mimeType"),
            "url":      a.get("content"),  # download URL
            "size":     a.get("size"),
        } for a in attachments]

    def extract_images_from_description(self, issue_key: str) -> list:
        """
        Fetch embedded images from Jira issue.
        Returns list of {filename, base64_data, mime_type}
        for use with vision LLM.
        """
        import base64
        results = []

        # Method 1: Attachments
        attachments = self.get_attachments(issue_key)
        image_attachments = [
            a for a in attachments
            if a["mimeType"].startswith("image/")
        ]

        for att in image_attachments[:5]:  # max 5 images
            try:
                with httpx.Client() as client:
                    r = client.get(
                        att["url"],
                        headers=self.headers,
                        follow_redirects=True,
                        timeout=30
                    )
                if r.status_code == 200:
                    b64 = base64.b64encode(r.content).decode()
                    results.append({
                        "filename":  att["filename"],
                        "mime_type": att["mimeType"],
                        "base64":    b64,
                        "size":      att["size"],
                    })
                    logger.info("image_fetched", filename=att["filename"])
            except Exception as e:
                logger.warning("image_fetch_failed", filename=att["filename"], error=str(e))

        return results

    async def describe_images_with_llm(self, issue_key: str) -> str:
        """
        Fetch images from Jira issue and describe them using vision LLM.
        Returns text description of all images for use as agent context.
        """
        images = self.extract_images_from_description(issue_key)
        if not images:
            return ""

        try:
            import anthropic
            import os
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

            descriptions = []
            for img in images:
                response = client.messages.create(
                    model="claude-sonnet-4-5-20250514",
                    max_tokens=500,
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": img["mime_type"],
                                    "data": img["base64"],
                                }
                            },
                            {
                                "type": "text",
                                "text": "Describe this UI screenshot for QA test case generation. Focus on: UI elements visible, user flows shown, error states, empty states, or design specs."
                            }
                        ]
                    }]
                )
                desc = response.content[0].text
                descriptions.append(f"[Image: {img['filename']}]\n{desc}")
                logger.info("image_described", filename=img["filename"])

            return "\n\n".join(descriptions)

        except Exception as e:
            logger.warning("vision_llm_failed", error=str(e))
            return f"[{len(images)} images found but vision LLM unavailable — set ANTHROPIC_API_KEY]"

    def get_transitions(self, issue_key: str) -> list:
        with httpx.Client() as client:
            r = client.get(
                f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions",
                headers=self.headers
            )
        return r.json().get("transitions", [])

    def transition_issue(self, issue_key: str, status_name: str) -> bool:
        transitions = self.get_transitions(issue_key)
        transition_id = next(
            (t["id"] for t in transitions if t["name"].upper() == status_name.upper()),
            None
        )
        if not transition_id:
            logger.warning("transition_not_found", issue=issue_key, status=status_name)
            return False
        with httpx.Client() as client:
            r = client.post(
                f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions",
                headers=self.headers,
                json={"transition": {"id": transition_id}}
            )
        return r.status_code == 204

    def add_comment(self, issue_key: str, comment: str) -> bool:
        with httpx.Client() as client:
            r = client.post(
                f"{self.base_url}/rest/api/3/issue/{issue_key}/comment",
                headers=self.headers,
                json={"body": {
                    "type": "doc", "version": 1,
                    "content": [{"type": "paragraph", "content": [
                        {"type": "text", "text": comment}
                    ]}]
                }}
            )
        return r.status_code == 201

    def search(self, jql: str, max_results: int = 10) -> list:
        with httpx.Client() as client:
            r = client.get(
                f"{self.base_url}/rest/api/3/search/jql",
                headers=self.headers,
                params={"jql": jql, "maxResults": max_results,
                        "fields": "summary,status,issuetype,assignee,priority"}
            )
        return [{
            "key":      i["key"],
            "summary":  i["fields"].get("summary", ""),
            "status":   i["fields"].get("status", {}).get("name", ""),
            "type":     i["fields"].get("issuetype", {}).get("name", ""),
            "assignee": (i["fields"].get("assignee") or {}).get("displayName", "Unassigned"),
        } for i in r.json().get("issues", [])]

    def post_test_results(self, issue_key: str, passed: int,
                          failed: int, skipped: int, run_url: str = "") -> bool:
        total = passed + failed + skipped
        icon  = "✅" if failed == 0 else "❌"
        rate  = f"{(passed/total*100):.0f}%" if total > 0 else "0%"
        comment = (
            f"{icon} QA Automation Results\n\n"
            f"Total: {total} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}\n"
            f"Pass rate: {rate}"
        )
        if run_url:
            comment += f"\nRun: {run_url}"
        return self.add_comment(issue_key, comment)


jira_client = JiraClient()
