"""Check whether approved test cases have enough executable evidence for codegen."""

from __future__ import annotations

from typing import Any


def _platform_evidence(evidence: dict[str, Any], platform: str) -> dict[str, Any]:
    if platform in {"android", "ios"}:
        return evidence.get(platform) or evidence.get("mobile") or {}
    return evidence.get(platform) or {}


def _has_any(data: dict[str, Any], keys: tuple[str, ...]) -> bool:
    return any(bool(data.get(key)) for key in keys)


def _missing(platform: str, evidence_type: str, message: str) -> dict[str, str]:
    return {
        "platform": platform,
        "type": evidence_type,
        "message": message,
    }


def _check_api(platform_evidence: dict[str, Any]) -> list[dict[str, str]]:
    missing = []
    if not _has_any(platform_evidence, ("curl", "endpoint", "openapi", "api_spec")):
        missing.append(_missing("api", "api_contract", "No curl, endpoint, OpenAPI, or API spec evidence provided."))
    if not _has_any(platform_evidence, ("method", "curl", "openapi", "api_spec")):
        missing.append(_missing("api", "method", "HTTP method is not known."))
    if not _has_any(platform_evidence, ("expected_status", "response_schema", "openapi", "api_spec")):
        missing.append(_missing("api", "expected_result", "Expected status or response schema is not known."))
    return missing


def _check_mobile(platform: str, platform_evidence: dict[str, Any]) -> list[dict[str, str]]:
    missing = []
    if not _has_any(platform_evidence, ("flow_steps", "navigation_path", "screen_sequence")):
        missing.append(_missing(platform, "actual_steps", "Actual mobile navigation/step flow evidence is missing."))
    if not _has_any(platform_evidence, ("locators", "app_source", "page_source", "accessibility_ids")):
        missing.append(_missing(platform, "locator", "No validated locator map, app source, or accessibility evidence provided."))
    if not _has_any(platform_evidence, ("test_data", "account_state", "preconditions")):
        missing.append(_missing(platform, "test_data", "Mobile test data/precondition evidence is missing."))
    return missing


def _check_web(platform_evidence: dict[str, Any], feature_url: str = "") -> list[dict[str, str]]:
    missing = []
    if not (feature_url or _has_any(platform_evidence, ("url", "route"))):
        missing.append(_missing("web", "url", "No web URL or route evidence provided."))
    if not _has_any(platform_evidence, ("flow_steps", "navigation_path", "user_flow")):
        missing.append(_missing("web", "actual_steps", "Actual web navigation/step flow evidence is missing."))
    if not _has_any(platform_evidence, ("selectors", "dom_snapshot", "accessibility_snapshot", "locators")):
        missing.append(_missing("web", "selector", "No selector, DOM, accessibility, or locator evidence provided."))
    return missing


def check_automation_readiness(state: dict[str, Any]) -> dict[str, Any]:
    """Return readiness status without mutating files or generating code."""
    platforms = state.get("platforms") or ["web"]
    evidence = state.get("automation_evidence") or {}
    source_bundle = state.get("source_bundle") or {}
    feature_url = state.get("feature_url") or source_bundle.get("feature_url") or ""
    missing_evidence: list[dict[str, str]] = []
    available_evidence: list[dict[str, str]] = []

    if state.get("testcase_output") or state.get("testcase_exports"):
        available_evidence.append({
            "platform": "all",
            "type": "approved_test_cases",
            "source": "testcase_output/testcase_exports",
        })
    else:
        missing_evidence.append(_missing("all", "approved_test_cases", "Approved test cases are required before automation codegen."))

    for platform in platforms:
        data = _platform_evidence(evidence, platform)
        if data:
            available_evidence.append({
                "platform": platform,
                "type": "execution_evidence",
                "source": "automation_evidence",
            })

        if platform == "api":
            missing_evidence.extend(_check_api(data))
        elif platform in {"android", "ios"}:
            missing_evidence.extend(_check_mobile(platform, data))
        elif platform == "web":
            missing_evidence.extend(_check_web(data, feature_url=feature_url))
        else:
            missing_evidence.append(_missing(platform, "platform", f"Unsupported automation platform: {platform}"))

    status = "ready" if not missing_evidence else "blocked"
    return {
        "status": status,
        "platforms": platforms,
        "available_evidence": available_evidence,
        "missing_evidence": missing_evidence,
        "codegen_allowed": status == "ready",
        "policy": (
            "AI can generate automation only from approved test cases and "
            "explicit executable flow evidence. Do not invent steps, locators, payloads, or assertions."
        ),
    }
