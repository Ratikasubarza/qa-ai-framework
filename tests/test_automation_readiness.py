import json

import pytest

from core.automation_readiness import (
    check_automation_readiness,
    load_automation_evidence,
    normalize_automation_evidence,
)


def test_api_readiness_blocks_without_contract_evidence():
    result = check_automation_readiness({
        "platforms": ["api"],
        "testcase_exports": {"csv": "reports/test.csv"},
    })

    assert result["status"] == "blocked"
    assert result["codegen_allowed"] is False
    assert {item["type"] for item in result["missing_evidence"]} >= {
        "api_contract",
        "method",
        "expected_result",
    }


def test_api_readiness_allows_curl_and_expected_status():
    result = check_automation_readiness({
        "platforms": ["api"],
        "testcase_exports": {"csv": "reports/test.csv"},
        "automation_evidence": {
            "api": {
                "curl": "curl -X POST https://api-dev.thehono.com/v1/posts",
                "expected_status": 201,
            }
        },
    })

    assert result["status"] == "ready"
    assert result["codegen_allowed"] is True


def test_android_readiness_blocks_without_steps_and_locators():
    result = check_automation_readiness({
        "platforms": ["android"],
        "testcase_exports": {"csv": "reports/test.csv"},
    })

    assert result["status"] == "blocked"
    assert {item["type"] for item in result["missing_evidence"]} >= {
        "actual_steps",
        "locator",
        "test_data",
    }


def test_android_readiness_allows_explicit_flow_locator_and_data():
    result = check_automation_readiness({
        "platforms": ["android"],
        "testcase_exports": {"csv": "reports/test.csv"},
        "automation_evidence": {
            "android": {
                "flow_steps": ["Open profile", "Tap Posts tab"],
                "accessibility_ids": ["Profile", "Posts"],
                "test_data": {"user": "approved synthetic user"},
            }
        },
    })

    assert result["status"] == "ready"
    assert result["codegen_allowed"] is True


def test_web_readiness_blocks_without_selector_evidence():
    result = check_automation_readiness({
        "platforms": ["web"],
        "feature_url": "https://app-dev.thehono.com/profile",
        "testcase_exports": {"csv": "reports/test.csv"},
        "automation_evidence": {
            "web": {"flow_steps": ["Open profile", "Click Posts tab"]}
        },
    })

    assert result["status"] == "blocked"
    assert any(item["type"] == "selector" for item in result["missing_evidence"])


def test_load_automation_evidence_accepts_platform_map_and_redacts_secrets(tmp_path):
    evidence_path = tmp_path / "hm_516_api.json"
    evidence_path.write_text(json.dumps({
        "api": {
            "curl": "curl -H 'Authorization: Bearer secret-token' https://api-dev.thehono.com/v1/posts",
            "method": "GET",
            "expected_status": 200,
        }
    }))

    evidence = load_automation_evidence(evidence_path)

    assert evidence["api"]["method"] == "GET"
    assert "secret-token" not in evidence["api"]["curl"]
    assert "[REDACTED_AUTH_HEADER]" in evidence["api"]["curl"]


def test_normalize_automation_evidence_accepts_evidence_envelope():
    evidence = normalize_automation_evidence({
        "feature": "HM-516",
        "evidence": {
            "android": {
                "flow_steps": ["Open profile", "Tap Posts tab"],
                "accessibility_ids": ["Profile", "Posts"],
                "test_data": {"user": "synthetic approved user"},
            }
        },
    })

    assert evidence == {
        "android": {
            "flow_steps": ["Open profile", "Tap Posts tab"],
            "accessibility_ids": ["Profile", "Posts"],
            "test_data": {"user": "synthetic approved user"},
        }
    }


def test_normalize_automation_evidence_rejects_unknown_shape():
    with pytest.raises(ValueError, match="platform key"):
        normalize_automation_evidence({"feature": "HM-516"})
