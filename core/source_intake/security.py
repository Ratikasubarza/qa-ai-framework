"""Security helpers for credentialed source text before LLM usage."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RedactionResult:
    text: str
    redactions: list[str]


REDACTION_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "authorization_header",
        re.compile(r"(?i)\b(authorization\s*:\s*)(bearer|basic)\s+[A-Za-z0-9._~+/=-]+"),
        r"\1[REDACTED_AUTH_HEADER]",
    ),
    (
        "bearer_token",
        re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+"),
        "Bearer [REDACTED_TOKEN]",
    ),
    (
        "api_key",
        re.compile(r"(?i)\b(api[_-]?key|token|secret)\s*[:=]\s*['\"]?[^'\"\s,;]+"),
        r"\1=[REDACTED_SECRET]",
    ),
    (
        "cookie",
        re.compile(r"(?i)\b(cookie\s*:\s*)[^\n\r]+"),
        r"\1[REDACTED_COOKIE]",
    ),
    (
        "password",
        re.compile(r"(?i)\b(password|passwd|pwd)\s*[:=]\s*['\"]?[^'\"\s,;]+"),
        r"\1=[REDACTED_PASSWORD]",
    ),
    (
        "email",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "[REDACTED_EMAIL]",
    ),
    (
        "phone",
        re.compile(r"(?<!\d)(?:\+\d[\d\s().-]{7,}\d|\d{2,}[\s().-]\d[\d\s().-]{5,}\d)(?!\d)"),
        "[REDACTED_PHONE]",
    ),
)


def redact_internal_text(text: str) -> RedactionResult:
    """Redact secrets and personal data from text sent to LLM agents."""
    redacted = text or ""
    applied: list[str] = []

    for name, pattern, replacement in REDACTION_PATTERNS:
        redacted, count = pattern.subn(replacement, redacted)
        if count:
            applied.append(name)

    return RedactionResult(text=redacted, redactions=applied)
