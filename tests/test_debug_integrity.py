from agents.debug_agent import DebugAgent, FailureContext


def test_debug_agent_disallows_auto_fix_for_product_bug(monkeypatch):
    agent = DebugAgent()

    monkeypatch.setattr(
        agent.breaker,
        "call",
        lambda call: type("Response", (), {
            "content": """
            {
              "root_cause": "API returns 500 for a valid request",
              "bug_type": "api_bug",
              "failure_classification": "PRODUCT_BUG",
              "confidence": 0.95,
              "recommended_action": "create_bug_report",
              "auto_fix_allowed": true,
              "integrity_notes": ["Preserve failing API assertion"],
              "severity": "P1",
              "title": "Valid post creation returns 500",
              "description": "Backend returns 500 for valid payload",
              "steps_to_reproduce": ["Run API test"],
              "expected_behavior": "201 Created",
              "actual_behavior": "500 Internal Server Error",
              "affected_component": "Post API",
              "suggested_fix": "Developer should inspect server error",
              "needs_dev_attention": true,
              "labels": ["ai-detected"]
            }
            """
        })(),
    )

    report = agent.analyze(FailureContext(
        test_name="test_create_post",
        error_message="Expected 201 but got 500",
        platform="api",
    ))

    assert report.failure_classification == "PRODUCT_BUG"
    assert report.auto_fix_allowed is False
    assert report.recommended_action == "create_bug_report"


def test_debug_agent_allows_high_confidence_locator_fix(monkeypatch):
    agent = DebugAgent()

    monkeypatch.setattr(
        agent.breaker,
        "call",
        lambda call: type("Response", (), {
            "content": """
            {
              "root_cause": "Locator no longer matches the same Posts tab element",
              "bug_type": "test_code",
              "failure_classification": "LOCATOR_CHANGED",
              "confidence": 0.91,
              "recommended_action": "update_locator",
              "auto_fix_allowed": true,
              "integrity_notes": ["Same intended element is visible with a stable accessibility id"],
              "severity": "P2",
              "title": "Posts tab locator is stale",
              "description": "Locator changed but behavior is correct",
              "steps_to_reproduce": ["Run Android test"],
              "expected_behavior": "Tap Posts tab",
              "actual_behavior": "Element not found",
              "affected_component": "Profile Posts tab test",
              "suggested_fix": "Update locator to accessibility id Posts",
              "needs_dev_attention": false,
              "labels": ["ai-detected"]
            }
            """
        })(),
    )

    report = agent.analyze(FailureContext(
        test_name="test_posts_tab",
        error_message="NoSuchElementException",
        platform="android",
    ))

    assert report.failure_classification == "LOCATOR_CHANGED"
    assert report.auto_fix_allowed is True
    assert report.recommended_action == "update_locator"
