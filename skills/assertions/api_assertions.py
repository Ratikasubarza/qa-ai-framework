"""
API Assertions — unified, chainable assertion layer for HTTP responses.

Wraps and extends SchemaValidator with:
- Domain-specific assertions (has_token, has_user_id)
- Allure attachment on failure
- Consistent error messages for the debug agent to parse

Usage:
    APIAssertions(response).status(200).has_token().response_time_under(3000)
    APIAssertions(response).status(400).body_contains_error("email")
"""
import allure
import structlog
from typing import Any

logger = structlog.get_logger(__name__)


class APIAssertions:
    def __init__(self, response):
        self.response = response
        try:
            self.body = response.json() if response.content else {}
        except Exception:
            self.body = {}

    # ── Status ────────────────────────────────────────────────────────────────

    def status(self, expected: int) -> "APIAssertions":
        actual = self.response.status_code
        assert actual == expected, (
            f"[APIAssertions] Status mismatch.\n"
            f"  Expected : {expected}\n"
            f"  Actual   : {actual}\n"
            f"  Body     : {str(self.body)[:300]}"
        )
        logger.debug("assert_status", expected=expected, actual=actual)
        return self

    def status_2xx(self) -> "APIAssertions":
        actual = self.response.status_code
        assert 200 <= actual < 300, (
            f"[APIAssertions] Expected 2xx, got {actual}\n"
            f"  Body: {str(self.body)[:300]}"
        )
        return self

    def status_in(self, *codes: int) -> "APIAssertions":
        actual = self.response.status_code
        assert actual in codes, (
            f"[APIAssertions] Status {actual} not in expected {codes}\n"
            f"  Body: {str(self.body)[:300]}"
        )
        return self

    # ── Body keys ─────────────────────────────────────────────────────────────

    def has_key(self, key: str) -> "APIAssertions":
        data = self.body.get("data", self.body)
        target = data if isinstance(data, dict) else self.body
        assert key in target, (
            f"[APIAssertions] Key '{key}' missing in response.\n"
            f"  Available keys: {list(target.keys())}"
        )
        return self

    def has_keys(self, *keys: str) -> "APIAssertions":
        for key in keys:
            self.has_key(key)
        return self

    def key_equals(self, key: str, expected: Any) -> "APIAssertions":
        actual = self.body.get(key)
        assert actual == expected, (
            f"[APIAssertions] '{key}' value mismatch.\n"
            f"  Expected : {expected}\n"
            f"  Actual   : {actual}"
        )
        return self

    def key_not_null(self, key: str) -> "APIAssertions":
        data = self.body.get("data", self.body)
        target = data if isinstance(data, dict) else self.body
        assert target.get(key) is not None, (
            f"[APIAssertions] Key '{key}' is null/missing — expected a value."
        )
        return self

    def key_is_list(self, key: str) -> "APIAssertions":
        val = self.body.get(key)
        assert isinstance(val, list), (
            f"[APIAssertions] '{key}' should be a list, got {type(val).__name__}"
        )
        return self

    def list_not_empty(self, key: str) -> "APIAssertions":
        self.key_is_list(key)
        assert len(self.body[key]) > 0, (
            f"[APIAssertions] List '{key}' is empty."
        )
        return self

    # ── Domain-specific: Auth ─────────────────────────────────────────────────

    def has_token(self) -> "APIAssertions":
        """Assert accessToken or token is present and non-empty."""
        data = self.body.get("data", self.body)
        target = data if isinstance(data, dict) else self.body
        token = target.get("accessToken") or target.get("token")
        assert token, (
            f"[APIAssertions] No token found in response.\n"
            f"  Body: {str(self.body)[:300]}"
        )
        return self

    def no_token(self) -> "APIAssertions":
        """Assert no token returned — for failed auth tests."""
        data = self.body.get("data", self.body)
        target = data if isinstance(data, dict) else self.body
        token = target.get("accessToken") or target.get("token")
        assert not token, (
            f"[APIAssertions] Token should NOT be present but got: {str(token)[:80]}"
        )
        return self

    # ── Domain-specific: Error responses ─────────────────────────────────────

    def body_contains_error(self, keyword: str) -> "APIAssertions":
        """Assert error message contains keyword — case-insensitive."""
        raw = str(self.body).lower()
        assert keyword.lower() in raw, (
            f"[APIAssertions] Error keyword '{keyword}' not found in response.\n"
            f"  Body: {str(self.body)[:300]}"
        )
        return self

    def code_equals(self, expected_code: str) -> "APIAssertions":
        actual = self.body.get("code", "")
        assert actual == expected_code, (
            f"[APIAssertions] Response code mismatch.\n"
            f"  Expected : '{expected_code}'\n"
            f"  Actual   : '{actual}'"
        )
        return self

    # ── Performance ───────────────────────────────────────────────────────────

    def response_time_under(self, ms: int) -> "APIAssertions":
        elapsed = self.response.elapsed.total_seconds() * 1000
        assert elapsed < ms, (
            f"[APIAssertions] Response time {elapsed:.0f}ms exceeded {ms}ms SLA."
        )
        logger.debug("assert_response_time", elapsed_ms=round(elapsed), limit_ms=ms)
        return self

    # ── Nested access ─────────────────────────────────────────────────────────

    def get(self, *keys) -> Any:
        """Navigate nested keys: .get('data', 'user', 'id')"""
        val = self.body
        for k in keys:
            assert isinstance(val, dict) and k in val, (
                f"[APIAssertions] Nested path {'→'.join(str(x) for x in keys)} "
                f"failed at '{k}'. Available: {list(val.keys()) if isinstance(val, dict) else type(val)}"
            )
            val = val[k]
        return val

    # ── Allure attachment ─────────────────────────────────────────────────────

    def attach_to_report(self, name: str = "Response") -> "APIAssertions":
        """Attach response body to Allure report."""
        try:
            import json
            allure.attach(
                json.dumps(self.body, indent=2, default=str),
                name=name,
                attachment_type=allure.attachment_type.JSON,
            )
        except Exception:
            pass
        return self
