"""
Confluence client for PRD intake.

Uses the same Atlassian email/token credentials as Jira. This keeps PRD fetching
separate from Jira issue fetching while preserving one credential model.
"""
from __future__ import annotations

import base64
import html
import os
import re
from html.parser import HTMLParser
from typing import Any

import httpx
import structlog
from dotenv import load_dotenv

MODEL_VISION = "claude-sonnet-4-6"

load_dotenv(dotenv_path=".env")
logger = structlog.get_logger(__name__)


class _ConfluenceStorageTextParser(HTMLParser):
    """Convert Confluence storage HTML into readable plain text."""

    BLOCK_TAGS = {
        "address", "blockquote", "div", "h1", "h2", "h3", "h4", "h5", "h6",
        "p", "pre", "section", "tr",
    }

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.BLOCK_TAGS:
            self._newline()
        elif tag == "br":
            self._newline()
        elif tag == "li":
            self._newline()
            self.parts.append("- ")
        elif tag in {"td", "th"}:
            self.parts.append(" | ")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.BLOCK_TAGS or tag in {"li", "table"}:
            self._newline()

    def handle_data(self, data: str) -> None:
        text = html.unescape(data).strip()
        if text:
            self.parts.append(text)
            self.parts.append(" ")

    def _newline(self) -> None:
        if self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n")

    def get_text(self) -> str:
        text = "".join(self.parts)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()


class ConfluenceClient:
    def __init__(self):
        self.base_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
        self.email = os.getenv("JIRA_EMAIL", "")
        self.token = os.getenv("JIRA_TOKEN", "")
        auth = base64.b64encode(f"{self.email}:{self.token}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {auth}",
            "Accept": "application/json",
        }

    @staticmethod
    def extract_page_id(page_url_or_id: str) -> str:
        """Extract Confluence page id from a URL or raw id."""
        value = (page_url_or_id or "").strip()
        if re.fullmatch(r"\d+", value):
            return value

        patterns = [
            r"/pages/(\d+)",
            r"/content/(\d+)",
            r"[?&]pageId=(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, value)
            if match:
                return match.group(1)

        raise ValueError(f"Could not extract Confluence page id from: {page_url_or_id}")

    @staticmethod
    def storage_html_to_text(storage_html: str) -> str:
        parser = _ConfluenceStorageTextParser()
        parser.feed(storage_html or "")
        return parser.get_text()

    def fetch_page(self, page_url_or_id: str) -> dict[str, Any]:
        """Fetch a Confluence page and return normalized PRD content."""
        if not self.base_url:
            raise ValueError("JIRA_BASE_URL is required for Confluence access.")
        if not self.email or not self.token:
            raise ValueError("JIRA_EMAIL and JIRA_TOKEN are required for Confluence access.")

        page_id = self.extract_page_id(page_url_or_id)
        api_url = f"{self.base_url}/wiki/rest/api/content/{page_id}"

        with httpx.Client(timeout=30) as client:
            response = client.get(
                api_url,
                headers=self.headers,
                params={"expand": "body.storage,title,space,version"},
            )

        if response.status_code == 401:
            raise PermissionError("Confluence authentication failed with 401.")
        if response.status_code == 403:
            raise PermissionError("Confluence page access is forbidden with 403.")
        if response.status_code == 404:
            raise FileNotFoundError(f"Confluence page not found or hidden: {page_id}")
        response.raise_for_status()

        data = response.json()
        body_html = (
            data.get("body", {})
            .get("storage", {})
            .get("value", "")
        )
        body_text = self.storage_html_to_text(body_html)
        title = data.get("title", "")
        space_key = data.get("space", {}).get("key", "")

        logger.info("confluence_page_fetched", page_id=page_id, title=title)
        return {
            "id": page_id,
            "title": title,
            "space_key": space_key,
            "source_url": page_url_or_id,
            "body_html": body_html,
            "body_text": body_text,
            "version": data.get("version", {}).get("number"),
        }

    def fetch_attachments(self, page_id: str) -> list[dict]:
        """Return image attachments for a Confluence page (id, filename, mime_type, download_url)."""
        api_url = f"{self.base_url}/wiki/rest/api/content/{page_id}/child/attachment"
        try:
            with httpx.Client(timeout=30) as client:
                r = client.get(api_url, headers=self.headers, params={"limit": 50})
            r.raise_for_status()
        except Exception as e:
            logger.warning("confluence_attachments_failed", page_id=page_id, error=str(e))
            return []

        results = []
        for att in r.json().get("results", []):
            mime = att.get("metadata", {}).get("mediaType", "")
            if not mime.startswith("image/"):
                continue
            dl_path = att.get("_links", {}).get("download", "")
            results.append({
                "id":           att.get("id", ""),
                "filename":     att.get("title", ""),
                "mime_type":    mime,
                "download_url": f"{self.base_url}/wiki{dl_path}" if dl_path else "",
            })
        logger.info("confluence_attachments_found", page_id=page_id, count=len(results))
        return results

    def _download_image_b64(self, download_url: str) -> str | None:
        """Download an image and return its base64 encoding."""
        try:
            with httpx.Client(timeout=30) as client:
                r = client.get(download_url, headers=self.headers, follow_redirects=True)
            if r.status_code == 200:
                return base64.b64encode(r.content).decode()
        except Exception as e:
            logger.warning("confluence_image_download_failed", url=download_url, error=str(e))
        return None

    def describe_images_with_llm(self, page_id: str) -> str:
        """
        Fetch all image attachments from a Confluence page and describe them using vision LLM.
        Returns a text block with descriptions of all images, suitable for AC extraction context.
        """
        attachments = self.fetch_attachments(page_id)
        if not attachments:
            return ""

        images = []
        for att in attachments[:5]:  # max 5 images
            b64 = self._download_image_b64(att["download_url"])
            if b64:
                images.append({**att, "base64": b64})

        if not images:
            return ""

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
            descriptions = []
            for img in images:
                response = client.messages.create(
                    model=MODEL_VISION,
                    max_tokens=600,
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": img["mime_type"],
                                    "data": img["base64"],
                                },
                            },
                            {
                                "type": "text",
                                "text": (
                                    "You are helping a QA engineer extract acceptance criteria from a PRD.\n"
                                    "Describe this image in detail: UI screens, flow diagrams, wireframes, or design specs shown. "
                                    "List every visible UI element, state, action, and label. "
                                    "If it shows a user flow, describe each step. "
                                    "If it shows an error or empty state, describe it explicitly."
                                ),
                            },
                        ],
                    }],
                )
                desc = response.content[0].text
                descriptions.append(f"[Attachment: {img['filename']}]\n{desc}")
                logger.info("confluence_image_described", filename=img["filename"])

            return "\n\n".join(descriptions)

        except Exception as e:
            logger.warning("confluence_vision_failed", error=str(e))
            return f"[{len(images)} image(s) found but vision LLM unavailable — set ANTHROPIC_API_KEY]"


confluence_client = ConfluenceClient()
