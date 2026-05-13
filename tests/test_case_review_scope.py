from core.case_review import normalize_review_scope


def test_android_review_does_not_block_api_only_missing_case():
    result = normalize_review_scope(
        target_platforms=["android"],
        missing_test_cases=[
            {
                "priority": "P0",
                "title": "Verify API payload excludes blocked user IDs",
                "reason": "Backend API contract should filter blocked users.",
            }
        ],
        detailed_findings=[
            {
                "severity": "Critical",
                "issue": "API response body does not include expected schema coverage.",
            }
        ],
    )

    assert result["missing_test_cases"][0]["scope_classification"] == "cross_platform_related_risk"
    assert result["missing_test_cases"][0]["blocking"] is False
    assert result["detailed_findings"][0]["scope_classification"] == "cross_platform_related_risk"
    assert result["detailed_findings"][0]["blocking"] is False
    assert result["summary"]["blocking_missing_count"] == 0
    assert result["summary"]["blocking_critical_count"] == 0
    assert result["summary"]["cross_platform_risk_count"] == 2


def test_android_review_blocks_android_missing_case():
    result = normalize_review_scope(
        target_platforms=["android"],
        missing_test_cases=[
            {
                "priority": "P1",
                "title": "Verify scroll position is preserved after device orientation change",
                "reason": "Android device rotation can reset Posts tab state.",
            }
        ],
        detailed_findings=[],
    )

    assert result["missing_test_cases"][0]["scope_classification"] == "in_scope_missing"
    assert result["missing_test_cases"][0]["blocking"] is True
    assert result["summary"]["blocking_missing_count"] == 1


def test_api_review_does_not_block_ui_only_missing_case():
    result = normalize_review_scope(
        target_platforms=["api"],
        missing_test_cases=[
            {
                "priority": "P1",
                "title": "Validate Android empty state label on Posts tab",
                "reason": "Mobile UI should display an empty state.",
            }
        ],
        detailed_findings=[],
    )

    assert result["missing_test_cases"][0]["scope_classification"] == "cross_platform_related_risk"
    assert result["missing_test_cases"][0]["blocking"] is False
    assert result["summary"]["blocking_missing_count"] == 0


def test_security_marker_is_always_blocking():
    result = normalize_review_scope(
        target_platforms=["android"],
        missing_test_cases=[],
        detailed_findings=[
            {
                "severity": "Minor",
                "issue": "Generated test case includes a bearer token in test data.",
            }
        ],
    )

    assert result["detailed_findings"][0]["scope_classification"] == "security_blocker"
    assert result["detailed_findings"][0]["blocking"] is True
    assert result["summary"]["security_blocker_count"] == 1
