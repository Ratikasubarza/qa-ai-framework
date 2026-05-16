"""
Debug Agent Eval — automated quality gate for the Debug Agent.

Checks that root cause analysis:
  1. Assigns a valid P0–P3 severity matching expected range
  2. Produces a non-trivial root_cause string (≥20 chars)
  3. Does NOT recommend auto_fix_allowed=True for product bugs

CI blocks merge if pass rate < threshold.
"""
import pytest
from dataclasses import dataclass

from agents.debug_agent import debug_agent, FailureContext

THRESHOLD = 0.80

FIXTURES: list[dict] = [
    {
        "id":             "assertion_401_login",
        "test_name":      "test_TC_API_001_login_valid_credentials",
        "error_message":  "AssertionError: Expected status 200, got 401",
        "stack_trace": (
            "  response = await client.post('/v1/users/login', json={...})\n"
            "  assert response.status_code == 200\n"
            "AssertionError: Expected 200, got 401"
        ),
        "platform":           "api",
        "location":           "POST /v1/users/login",
        "expected_severities": ["P1", "P2"],
        "must_not_auto_fix":  True,
    },
    {
        "id":             "timeout_register",
        "test_name":      "test_TC_REG_API_001_register_valid_data",
        "error_message":  "httpx.TimeoutException: Request timed out after 30s",
        "stack_trace": (
            "  response = await client.post('/v1/users/register', json=payload)\n"
            "httpx.TimeoutException: timed out after 30.0s"
        ),
        "platform":           "api",
        "location":           "POST /v1/users/register",
        "expected_severities": ["P2", "P3"],
        "must_not_auto_fix":  False,   # may be environment, auto-fix acceptable
    },
    {
        "id":             "element_not_found_web",
        "test_name":      "test_login_button_visible",
        "error_message":  "TimeoutError: Waiting for selector '.login-btn-deprecated' failed",
        "stack_trace": (
            "  await page.click('.login-btn-deprecated')\n"
            "playwright._impl._api_types.TimeoutError:\n"
            "Waiting for selector '.login-btn-deprecated' timed out after 30000ms"
        ),
        "platform":           "web",
        "location":           "https://app-dev.thehono.com/login",
        "expected_severities": ["P1", "P2"],
        "must_not_auto_fix":  False,   # locator issue — auto-fix allowed
    },
    {
        "id":             "password_change_rejected",
        "test_name":      "test_TC_USERS_PASSWORD_001_change_password_success",
        "error_message":  "AssertionError: Old password should be rejected after successful change.",
        "stack_trace": (
            "  old_status = await login_status(email, CURRENT_PASSWORD)\n"
            "  assert old_status == 401\n"
            "AssertionError: Old password should be rejected after password change."
        ),
        "platform":           "api",
        "location":           "PUT /v1/users/me/password",
        "expected_severities": ["P1", "P2"],
        "must_not_auto_fix":  True,    # product/security bug — never auto-fix
    },
]


@dataclass
class DebugEvalResult:
    fixture_id:      str
    severity:        str
    root_cause:      str
    auto_fix:        bool
    severity_valid:  bool
    has_root_cause:  bool
    auto_fix_ok:     bool
    passed:          bool
    notes:           str = ""


def _evaluate_fixture(fx: dict) -> DebugEvalResult:
    failure = FailureContext(
        test_name=fx["test_name"],
        error_message=fx["error_message"],
        stack_trace=fx["stack_trace"],
        platform=fx["platform"],
        location=fx["location"],
    )
    report = debug_agent.analyze(failure)

    severity_valid = report.severity in fx["expected_severities"]
    has_root_cause = bool(report.root_cause and len(report.root_cause.strip()) >= 20)
    auto_fix_ok    = not (fx["must_not_auto_fix"] and report.auto_fix_allowed)

    passed = severity_valid and has_root_cause and auto_fix_ok

    return DebugEvalResult(
        fixture_id=fx["id"],
        severity=report.severity,
        root_cause=report.root_cause[:80] if report.root_cause else "",
        auto_fix=report.auto_fix_allowed,
        severity_valid=severity_valid,
        has_root_cause=has_root_cause,
        auto_fix_ok=auto_fix_ok,
        passed=passed,
        notes=(
            f"severity={report.severity} "
            f"(expected {fx['expected_severities']}) "
            f"auto_fix={report.auto_fix_allowed}"
        ),
    )


def test_eval_debug_agent():
    """
    Debug agent quality gate.
    Each fixture must: correct severity range, non-empty root cause,
    no auto_fix on product bugs.
    Fails if pass rate < threshold.
    """
    if not FIXTURES:
        pytest.skip("No debug agent fixtures defined")

    results = [_evaluate_fixture(fx) for fx in FIXTURES]

    for r in results:
        print(f"\n[DEBUG-EVAL] {r.fixture_id}")
        print(f"  Severity:   {r.severity} ({'✓' if r.severity_valid else '✗'})")
        print(f"  Root cause: {'✓' if r.has_root_cause else '✗'} — {r.root_cause[:60]}")
        print(f"  Auto-fix:   {'ok' if r.auto_fix_ok else 'BLOCKED (product bug marked auto-fix)'}")
        print(f"  Result:     {'PASS' if r.passed else 'FAIL'}")

    pass_rate = sum(1 for r in results if r.passed) / len(results)
    assert pass_rate >= THRESHOLD, (
        f"Debug agent eval pass rate {pass_rate:.0%} below threshold {THRESHOLD:.0%}\n"
        + "\n".join(f"  FAIL {r.fixture_id}: {r.notes}" for r in results if not r.passed)
    )
