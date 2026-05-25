"""
Input Sanitizer — defends against prompt injection.
Applied at every agent boundary before content enters the LLM context.
Sources at risk: Jira tickets, PRD docs, DOM snapshots, bug reports.
"""
import re
import base64
import hashlib
import structlog
from dataclasses import dataclass

logger = structlog.get_logger(__name__)

# ── Compiled injection patterns ───────────────────────────────────────────────

INJECTION_PATTERNS = [
    # Classic instruction overrides
    r"ignore\s+(all\s+)?previous\s+instructions?",
    r"you\s+are\s+now\s+",
    r"\bsystem\s*:",
    r"<\|.*?\|>",                                    # LLM delimiters (<|im_start|> etc.)
    r"\[INST\]",                                     # Llama 2 tag
    r"###\s*system",                                 # Mistral heading-style
    r"</?(prompt|system|user|assistant)>",           # XML role tags
    r"disregard\s+(all\s+)?previous",
    r"forget\s+(all\s+)?previous",
    # Extended
    r"\bact\s+as\s+",
    r"\bpretend\s+(you\s+are|to\s+be)\s+",
    r"\bnew\s+instructions?\s*:",
    r"(?!eyJ)[A-Za-z0-9+/]{30,}={1,2}",             # Padded base64 blobs (not JWT)
    r"[Ѐ-ӿͰ-Ͽ][a-zA-Z]",                           # Cyrillic/Greek adjacent to ASCII
    # ── New patterns ─────────────────────────────────────────────────────────
    # A: act-as variant — "from now on you are / will be"
    r"\bfrom\s+now\s+on\s+(?:you\s+)?(?:are|will\s+be)\s+",
    # B: DAN-style jailbreak phrases
    r"\b(?:DAN\s+mode|do\s+anything\s+now|developer\s+mode\s+enabled)\b",
    # E1: Mistral-heading expansion — user/human/assistant with colon guard
    r"###\s*(?:user|human|assistant)\s*:",
    # E2: System prompt override (colon guard avoids "new system prompt config" FP)
    r"\bnew\s+system\s+prompt\s*:",
    # E3: "ignore above/prior/earlier" with trailing noun (prevents "ignore prior failures" FP)
    r"\bignore\s+(?:the\s+)?(?:above|prior|earlier)\s+(?:instructions?|rules?|constraints?|guidelines?|prompts?|context)\b",
]

_COMPILED = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in INJECTION_PATTERNS]

# Separate finder for two-pass base64 decode — catches unpadded blobs pattern 13 misses
_B64_CANDIDATE = re.compile(r"[A-Za-z0-9+/]{50,}={0,2}", re.ASCII)

# Unicode codepoints used in homoglyph/BIDI evasion — explicit chr() for auditability
_BIDI_OVERRIDE_CHARS = frozenset({
    chr(0x202E),  # RIGHT-TO-LEFT OVERRIDE
    chr(0x202D),  # LEFT-TO-RIGHT OVERRIDE
})
_INVISIBLE_CHARS = frozenset({
    chr(0x200B),  # ZERO WIDTH SPACE
    chr(0x200C),  # ZERO WIDTH NON-JOINER
    chr(0x200D),  # ZERO WIDTH JOINER
    chr(0xFEFF),  # BOM / ZERO WIDTH NO-BREAK SPACE
    chr(0x2060),  # WORD JOINER
})
_WARN_ONLY_CHARS = frozenset({chr(0x00AD)})  # SOFT HYPHEN — warn but keep


@dataclass
class SanitizedInput:
    content:       str
    was_sanitized: bool
    threat_count:  int
    content_hash:  str
    source:        str


def _check_base64_encoded_instructions(content: str, source: str) -> tuple[list[str], str]:
    """
    Two-pass check: locate base64 candidates ≥50 chars, decode, then check
    decoded text against all compiled injection patterns.
    Only candidates whose decoded payload matches a known pattern are redacted —
    clean base64 (OAuth codes, HMAC signatures) passes through untouched.
    """
    threats: list[str] = []
    cleaned = content

    for match in _B64_CANDIDATE.finditer(content):
        candidate = match.group()
        padded = candidate + "=" * (-len(candidate) % 4)
        try:
            decoded = base64.b64decode(padded, validate=False).decode("utf-8", errors="ignore")
        except Exception:
            continue

        for pat in _COMPILED:
            if pat.search(decoded):
                label = candidate[:40] + ("…" if len(candidate) > 40 else "")
                threats.append(label)
                cleaned = cleaned.replace(candidate, "[REDACTED_B64]", 1)
                logger.warning(
                    "base64_injection_detected",
                    source=source,
                    candidate_prefix=candidate[:20],
                    decoded_preview=decoded[:80],
                )
                break

    return threats, cleaned


def _check_homoglyph_injection(content: str, source: str) -> tuple[list[str], str]:
    """
    Detect BIDI override characters and zero-width invisibles used to hide
    injected text or reverse displayed characters.
    - BIDI overrides  → replace with [REDACTED_BIDI]
    - Invisible chars → strip silently
    - Soft hyphen     → warn-only, kept in content
    """
    threats: list[str] = []
    out: list[str] = []

    for ch in content:
        if ch in _BIDI_OVERRIDE_CHARS:
            threats.append(f"BIDI:U+{ord(ch):04X}")
            out.append("[REDACTED_BIDI]")
            logger.warning(
                "bidi_override_detected",
                source=source,
                codepoint=f"U+{ord(ch):04X}",
            )
        elif ch in _INVISIBLE_CHARS:
            threats.append(f"INVIS:U+{ord(ch):04X}")
            logger.warning(
                "invisible_char_detected",
                source=source,
                codepoint=f"U+{ord(ch):04X}",
            )
            # Strip — do not append to output
        elif ch in _WARN_ONLY_CHARS:
            threats.append(f"SOFTHYPHEN:U+{ord(ch):04X}")
            out.append(ch)
            logger.info(
                "soft_hyphen_found",
                source=source,
                note="warn-only, character kept",
            )
        else:
            out.append(ch)

    return threats, "".join(out)


def sanitize(content: str, source: str = "unknown") -> SanitizedInput:
    """
    Scan content for injection patterns.
    Neutralizes threats by replacing with [REDACTED].
    Logs all sanitization events for audit trail.
    """
    original_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    threats_found: list[str] = []
    cleaned = content

    # Pass 1 — compiled regex patterns
    for pattern in _COMPILED:
        matches = pattern.findall(cleaned)
        if matches:
            threats_found.extend(matches)
            cleaned = pattern.sub("[REDACTED]", cleaned)

    # Pass 2 — base64-encoded instruction payloads (two-pass decode check)
    b64_threats, cleaned = _check_base64_encoded_instructions(cleaned, source)
    threats_found.extend(b64_threats)

    # Pass 3 — Unicode BIDI override and invisible character injection
    hg_threats, cleaned = _check_homoglyph_injection(cleaned, source)
    threats_found.extend(hg_threats)

    if threats_found:
        logger.warning(
            "injection_attempt_detected",
            source=source,
            threat_count=len(threats_found),
            content_hash=original_hash,
        )

    return SanitizedInput(
        content=cleaned,
        was_sanitized=bool(threats_found),
        threat_count=len(threats_found),
        content_hash=original_hash,
        source=source,
    )
