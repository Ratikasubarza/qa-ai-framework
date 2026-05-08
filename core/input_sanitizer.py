"""
Input Sanitizer — defends against prompt injection.
Applied at every agent boundary before content enters the LLM context.
Sources at risk: Jira tickets, PRD docs, DOM snapshots, bug reports.
"""
import re
import hashlib
import structlog
from dataclasses import dataclass, field

logger = structlog.get_logger(__name__)

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions?",
    r"you\s+are\s+now\s+",
    r"\bsystem\s*:",
    r"<\|.*?\|>",          # Common injection delimiters
    r"\[INST\]",            # Llama-style
    r"###\s*system",        # Mistral-style
    r"</?(prompt|system|user|assistant)>",
    r"disregard\s+(all\s+)?previous",
    r"forget\s+(all\s+)?previous",
]

_COMPILED = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in INJECTION_PATTERNS]


@dataclass
class SanitizedInput:
    content:       str
    was_sanitized: bool
    threat_count:  int
    content_hash:  str
    source:        str


def sanitize(content: str, source: str = "unknown") -> SanitizedInput:
    """
    Scan content for injection patterns.
    Neutralizes threats by replacing with [REDACTED].
    Logs all sanitization events for audit trail.
    """
    threats_found = []
    cleaned       = content

    for pattern in _COMPILED:
        matches = pattern.findall(content)
        if matches:
            threats_found.extend(matches)
            cleaned = pattern.sub("[REDACTED]", cleaned)

    if threats_found:
        logger.warning(
            "injection_attempt_detected",
            source=source,
            threat_count=len(threats_found),
            content_hash=hashlib.sha256(content.encode()).hexdigest()[:16],
        )

    return SanitizedInput(
        content=cleaned,
        was_sanitized=bool(threats_found),
        threat_count=len(threats_found),
        content_hash=hashlib.sha256(content.encode()).hexdigest()[:16],
        source=source,
    )
