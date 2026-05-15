"""Load and sanitize automation evidence files for code generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.source_intake.security import redact_internal_text

SUPPORTED_EVIDENCE_PLATFORMS = {
    "api",
    "web",
    "android",
    "ios",
    "mobile",
}


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_internal_text(value).text
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _redact_value(item) for key, item in value.items()}
    return value


def normalize_automation_evidence(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize supported evidence file shapes into a platform evidence map."""
    if not isinstance(raw, dict):
        raise ValueError("Automation evidence must be a JSON object.")

    evidence = raw.get("evidence", raw)
    if not isinstance(evidence, dict):
        raise ValueError("Automation evidence field must be a JSON object.")

    normalized = {
        str(platform).strip().lower(): data
        for platform, data in evidence.items()
        if str(platform).strip().lower() in SUPPORTED_EVIDENCE_PLATFORMS
    }
    if not normalized:
        raise ValueError(
            "Automation evidence must contain at least one platform key: "
            "api, web, android, ios, or mobile."
        )

    for platform, data in normalized.items():
        if not isinstance(data, dict):
            raise ValueError(f"Automation evidence for '{platform}' must be a JSON object.")

    return _redact_value(normalized)


def load_automation_evidence(path: str | Path | None) -> dict[str, Any]:
    """Load a local JSON evidence file and redact sensitive values."""
    if not path:
        return {}

    evidence_path = Path(path).expanduser()
    if not evidence_path.exists():
        raise FileNotFoundError(f"Automation evidence file not found: {evidence_path}")
    if evidence_path.suffix.lower() != ".json":
        raise ValueError("Automation evidence must be provided as a .json file.")

    try:
        raw = json.loads(evidence_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Automation evidence is not valid JSON: {exc}") from exc

    return normalize_automation_evidence(raw)
