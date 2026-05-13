from core.automation_readiness import check_automation_readiness


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
