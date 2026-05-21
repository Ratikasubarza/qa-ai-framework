"""
MCP Figma Client — Extract design specs from Figma for test coverage analysis.

Capabilities:
  - get_file()              : fetch Figma file metadata + top-level frame list
  - get_node()              : get a specific node (frame/component) by ID
  - extract_text_content()  : extract all visible text labels from a frame
  - extract_components()    : list component names (maps to UI elements for locator gen)
  - get_file_images()       : render frame as PNG URL (for visual regression baseline)

Env vars required:
  FIGMA_TOKEN               : Personal access token from Figma account settings
  FIGMA_FILE_KEY            : Figma file key (from file URL: figma.com/file/<KEY>/...)

Usage in test_case_agent / locator_agent:
    from integrations.figma_client import figma_client
    frames = figma_client.get_file()["frames"]
    labels = figma_client.extract_text_content(node_id="1234:5678")
"""
from __future__ import annotations

import os
import httpx
import structlog
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")
logger = structlog.get_logger(__name__)

_FIGMA_API = "https://api.figma.com/v1"


class FigmaClient:
    def __init__(self) -> None:
        self.token    = os.getenv("FIGMA_TOKEN", "")
        self.file_key = os.getenv("FIGMA_FILE_KEY", "")
        self._headers = {"X-Figma-Token": self.token}

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{_FIGMA_API}{path}"
        try:
            with httpx.Client(timeout=20) as client:
                resp = client.get(url, headers=self._headers, params=params or {})
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("figma_request_failed", path=path, error=str(e))
            return {}

    # ── File-level ────────────────────────────────────────────────────────────

    def get_file(self, file_key: str | None = None) -> dict:
        """Return file name + top-level frame names and IDs."""
        key = file_key or self.file_key
        if not key:
            logger.warning("figma_file_key_not_set")
            return {}
        data = self._get(f"/files/{key}", params={"depth": 2})
        doc  = data.get("document", {})
        frames = []
        for page in doc.get("children", []):
            for node in page.get("children", []):
                if node.get("type") in ("FRAME", "COMPONENT", "SECTION"):
                    frames.append({"id": node["id"], "name": node.get("name", ""), "type": node["type"]})
        return {
            "name":        data.get("name", ""),
            "last_modified": data.get("lastModified", ""),
            "frames":      frames,
        }

    def get_node(self, node_id: str, file_key: str | None = None) -> dict:
        """Fetch a specific Figma node by ID."""
        key = file_key or self.file_key
        if not key:
            return {}
        data = self._get(f"/files/{key}/nodes", params={"ids": node_id})
        nodes = data.get("nodes", {})
        return nodes.get(node_id, {}).get("document", {})

    # ── Text extraction ───────────────────────────────────────────────────────

    def extract_text_content(self, node_id: str, file_key: str | None = None) -> list[str]:
        """Return all visible text strings inside a Figma frame — useful for label/copy verification."""
        node = self.get_node(node_id, file_key)
        texts: list[str] = []
        self._collect_text(node, texts)
        return texts

    def _collect_text(self, node: dict, out: list[str]) -> None:
        if node.get("type") == "TEXT":
            chars = node.get("characters", "").strip()
            if chars:
                out.append(chars)
        for child in node.get("children", []):
            self._collect_text(child, out)

    # ── Component extraction ──────────────────────────────────────────────────

    def extract_components(self, node_id: str, file_key: str | None = None) -> list[dict]:
        """Return list of component nodes {id, name} — maps to UI elements for locator generation."""
        node = self.get_node(node_id, file_key)
        components: list[dict] = []
        self._collect_components(node, components)
        return components

    def _collect_components(self, node: dict, out: list[dict]) -> None:
        if node.get("type") in ("COMPONENT", "INSTANCE"):
            out.append({"id": node.get("id", ""), "name": node.get("name", "")})
        for child in node.get("children", []):
            self._collect_components(child, out)

    # ── Image rendering ───────────────────────────────────────────────────────

    def get_frame_image_url(
        self,
        node_id: str,
        file_key: str | None = None,
        scale: float = 1.0,
        fmt: str = "png",
    ) -> str:
        """Return a rendered PNG/JPG URL for the frame — use as visual regression baseline."""
        key = file_key or self.file_key
        if not key:
            return ""
        data = self._get(
            f"/images/{key}",
            params={"ids": node_id, "scale": scale, "format": fmt},
        )
        return data.get("images", {}).get(node_id, "")


figma_client = FigmaClient()
