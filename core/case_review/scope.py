"""Scope classification for AI case review findings."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


PLATFORM_MARKERS = {
    "api": (
        " api ",
        " endpoint",
        " payload",
        " schema",
        " status code",
        " response body",
        " request body",
        " contract",
        " rate limit",
        " 429",
        " backend",
        " database",
        " db ",
    ),
    "android": (
        " android ",
        " mobile ",
        " app ",
        " appium",
        " flutter",
        " device",
        " orientation",
        " scroll",
        " tap ",
        " ui ",
    ),
    "ios": (
        " ios ",
        " mobile ",
        " app ",
        " appium",
        " device",
        " orientation",
        " scroll",
        " tap ",
        " ui ",
    ),
    "web": (
        " web ",
        " browser",
        " frontend",
        " front-end",
        " cms ",
        " playwright",
        " page ",
        " dom ",
        " ui ",
    ),
}

SECURITY_MARKERS = (
    " token",
    " bearer",
    " cookie",
    " hardcoded password",
    " plain password",
    " password value",
    " secret",
    " api key",
    " private key",
    " credential",
    " .env",
)

CLARIFICATION_MARKERS = (
    " clarify",
    " clarification",
    " ambiguous",
    " unclear",
    " not specified",
    " exact text",
    " expected?",
)


def _text_from_item(item: Any) -> str:
    if isinstance(item, dict):
        fields = [
            item.get("title", ""),
            item.get("reason", ""),
            item.get("issue", ""),
            item.get("suggestion", ""),
            item.get("covers_requirement", ""),
            item.get("affected_test_case", ""),
        ]
        return f" {' '.join(str(field) for field in fields)} ".lower()
    return f" {item} ".lower()


def _platform_hits(text: str) -> set[str]:
    return {
        platform
        for platform, markers in PLATFORM_MARKERS.items()
        if any(marker in text for marker in markers)
    }


def classify_review_item(item: Any, target_platforms: list[str]) -> str:
    text = _text_from_item(item)
    if any(marker in text for marker in SECURITY_MARKERS):
        return "security_blocker"
    if any(marker in text for marker in CLARIFICATION_MARKERS):
        return "clarification_needed"

    targets = set(target_platforms or [])
    hits = _platform_hits(text)
    if hits and hits.isdisjoint(targets):
        return "cross_platform_related_risk"
    return "in_scope_missing"


def _normalize_item(item: Any, target_platforms: list[str]) -> dict:
    normalized = deepcopy(item) if isinstance(item, dict) else {"title": str(item)}
    classification = normalized.get("classification") or normalized.get("scope_classification")
    if classification not in {
        "in_scope_missing",
        "cross_platform_related_risk",
        "clarification_needed",
        "security_blocker",
    }:
        classification = classify_review_item(normalized, target_platforms)

    blocking = classification in {"in_scope_missing", "security_blocker"}
    normalized["scope_classification"] = classification
    normalized["blocking"] = bool(normalized.get("blocking", blocking))
    return normalized


def normalize_review_scope(
    missing_test_cases: list[Any],
    detailed_findings: list[Any],
    target_platforms: list[str],
) -> dict[str, Any]:
    normalized_missing = [
        _normalize_item(item, target_platforms)
        for item in (missing_test_cases or [])
    ]
    normalized_findings = [
        _normalize_item(item, target_platforms)
        for item in (detailed_findings or [])
    ]

    blocking_missing = [
        item for item in normalized_missing
        if item.get("blocking")
    ]
    blocking_findings = [
        item for item in normalized_findings
        if item.get("blocking") and str(item.get("severity", "")).lower() == "critical"
    ]
    cross_platform_risks = [
        item for item in [*normalized_missing, *normalized_findings]
        if item.get("scope_classification") == "cross_platform_related_risk"
    ]
    clarification_needed = [
        item for item in [*normalized_missing, *normalized_findings]
        if item.get("scope_classification") == "clarification_needed"
    ]
    security_blockers = [
        item for item in [*normalized_missing, *normalized_findings]
        if item.get("scope_classification") == "security_blocker"
    ]

    return {
        "missing_test_cases": normalized_missing,
        "detailed_findings": normalized_findings,
        "summary": {
            "blocking_missing_count": len(blocking_missing),
            "blocking_critical_count": len(blocking_findings),
            "cross_platform_risk_count": len(cross_platform_risks),
            "clarification_needed_count": len(clarification_needed),
            "security_blocker_count": len(security_blockers),
        },
    }
