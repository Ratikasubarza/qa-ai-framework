"""
Debug Agent Tests — verify analysis pipeline without creating Jira tickets.
"""
import pytest
from agents.debug_agent import debug_agent, FailureContext


def test_debug_agent_analyze_login_failure():
    """
    Verify Debug Agent can analyze a login test failure.
    Does NOT create Jira ticket.
    """
    failure = FailureContext(
        test_name="test_TC_WEB_001_login_button_disabled_when_empty",
        error_message="AssertionError: Element should be DISABLED but is enabled: 'Login button'",
        platform="web",
        location="https://app-dev.thehono.com/login",
        stack_trace=(
            "features/login/steps/login_web_test.py:86 in test_TC_WEB_001\n"
            "skills/base/assertion_helper.py:54 in element_disabled\n"
            "AssertionError: Element should be DISABLED but is enabled"
        ),
    )

    report = debug_agent.analyze(failure)

    assert report.title, "Bug title should not be empty"
    assert report.severity in ["P0", "P1", "P2", "P3"], f"Invalid severity: {report.severity}"
    assert report.bug_type, "Bug type should not be empty"
    assert report.root_cause, "Root cause should not be empty"
    assert len(report.steps_to_reproduce) > 0, "Should have steps to reproduce"

    print(f"\n✓ Bug Report Generated:")
    print(f"  Title:     {report.title}")
    print(f"  Severity:  {report.severity}")
    print(f"  Type:      {report.bug_type}")
    print(f"  Root cause: {report.root_cause[:80]}")


def test_debug_agent_analyze_api_failure():
    """Verify Debug Agent can analyze an API test failure."""
    failure = FailureContext(
        test_name="test_TC_API_006_search_authenticated",
        error_message="AssertionError: Status code assertion failed. Expected: 200 Actual: 400",
        platform="api",
        location="GET /v1/search/posts?q=test",
        stack_trace=(
            "features/login/steps/login_api_test.py:148\n"
            "skills/api/schema_validator.py:20 in status_ok\n"
            "AssertionError: Status code assertion failed"
        ),
        extra_context={"response_body": {"code": "NOKBADREQ", "message": "query is required"}},
    )

    report = debug_agent.analyze(failure)

    assert report.title
    assert report.severity in ["P0", "P1", "P2", "P3"]
    print(f"\n✓ API Bug Report:")
    print(f"  Title:     {report.title}")
    print(f"  Severity:  {report.severity}")
    print(f"  Type:      {report.bug_type}")


def test_debug_agent_severity_classification():
    """Verify severity classification is reasonable."""
    # P0 — login broken
    failure_p0 = FailureContext(
        test_name="test_login_smoke",
        error_message="Login not working — all users blocked from accessing the app",
        platform="web",
        location="https://app-dev.thehono.com/login",
    )
    report_p0 = debug_agent.analyze(failure_p0)
    assert report_p0.severity in ["P0", "P1"], f"Login failure should be P0/P1, got {report_p0.severity}"

    print(f"\n✓ Severity tests passed")
    print(f"  Login failure: {report_p0.severity}")
