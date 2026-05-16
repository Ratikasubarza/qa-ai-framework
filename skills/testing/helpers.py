"""Shared test helpers — plain functions importable across all test files."""
import pytest


def skip_on_email_quota(response) -> None:
    """Skip when Resend daily email quota is exhausted (platform limit, not a bug)."""
    if response.status_code == 500 and (
        "email sending quota" in response.text
        or "You have reached your daily email send" in response.text
    ):
        pytest.skip("Resend daily email quota reached — skip test")


def assert_required_keys(payload: dict, required_keys: set, label: str) -> None:
    """Assert that every key in required_keys exists in payload."""
    missing = required_keys - set(payload.keys())
    assert not missing, f"Missing {label} field(s): {sorted(missing)}"
