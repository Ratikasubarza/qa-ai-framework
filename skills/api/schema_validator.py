"""
Schema Validator — validates API response structure and values.
Used by API Test Agent to assert contract compliance.
"""
import structlog
from typing import Any

logger = structlog.get_logger(__name__)


class SchemaValidator:
    def __init__(self, response):
        self.response = response
        self.body     = response.json() if response.content else {}

    # ── Status Code Assertions ────────────────────────────────────────

    def status_is(self, expected: int):
        actual = self.response.status_code
        assert actual == expected, (
            f"Status code assertion failed.\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}\n"
            f"Body: {str(self.body)[:200]}"
        )
        logger.debug("assert_status", expected=expected, actual=actual)
        return self

    def status_ok(self):
        return self.status_is(200)

    def status_created(self):
        return self.status_is(201)

    def status_unauthorized(self):
        return self.status_is(401)

    def status_forbidden(self):
        return self.status_is(403)

    def status_not_found(self):
        return self.status_is(404)

    def status_2xx(self):
        actual = self.response.status_code
        assert 200 <= actual < 300, (
            f"Expected 2xx status, got {actual}\nBody: {str(self.body)[:200]}"
        )
        return self

    # ── Body Assertions ───────────────────────────────────────────────

    def has_key(self, key: str):
        assert key in self.body, (
            f"Key '{key}' not found in response.\n"
            f"Available keys: {list(self.body.keys())}"
        )
        return self

    def has_keys(self, *keys):
        for key in keys:
            self.has_key(key)
        return self

    def key_equals(self, key: str, expected: Any):
        self.has_key(key)
        actual = self.body[key]
        assert actual == expected, (
            f"Key '{key}' value mismatch.\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}"
        )
        return self

    def key_not_null(self, key: str):
        self.has_key(key)
        assert self.body[key] is not None, (
            f"Key '{key}' is null but should have a value."
        )
        return self

    def key_is_list(self, key: str):
        self.has_key(key)
        assert isinstance(self.body[key], list), (
            f"Key '{key}' should be a list, got {type(self.body[key]).__name__}"
        )
        return self

    def key_is_dict(self, key: str):
        self.has_key(key)
        assert isinstance(self.body[key], dict), (
            f"Key '{key}' should be a dict, got {type(self.body[key]).__name__}"
        )
        return self

    def list_not_empty(self, key: str):
        self.key_is_list(key)
        assert len(self.body[key]) > 0, (
            f"List '{key}' is empty but should have items."
        )
        return self

    def nested_key(self, *keys) -> Any:
        """Get nested value: nested_key('data', 'user', 'id')"""
        val = self.body
        for k in keys:
            assert isinstance(val, dict) and k in val, (
                f"Nested key path {' → '.join(str(x) for x in keys)} "
                f"failed at '{k}'. Available: {list(val.keys()) if isinstance(val, dict) else type(val)}"
            )
            val = val[k]
        return val

    def response_time_under(self, ms: int):
        elapsed = self.response.elapsed.total_seconds() * 1000
        assert elapsed < ms, (
            f"Response time {elapsed:.0f}ms exceeded {ms}ms limit."
        )
        logger.debug("assert_response_time", elapsed_ms=elapsed, limit_ms=ms)
        return self

    def code_equals(self, expected_code: str):
        """Assert response body 'code' field."""
        actual = self.body.get("code", "")
        assert actual == expected_code, (
            f"Response code mismatch.\n"
            f"Expected: '{expected_code}'\n"
            f"Actual:   '{actual}'"
        )
        return self
