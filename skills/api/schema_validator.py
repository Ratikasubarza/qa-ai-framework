"""
SchemaValidator — single, unified fluent assertion library for all API tests.

Canonical import across every test file:
    from skills.api.schema_validator import SchemaValidator

    SchemaValidator(response).status_ok().has_key("data").response_time_under(3000)
    SchemaValidator(response).status_in(200, 201).has_token()
    SchemaValidator(response).status_unauthorized()

Do NOT import skills.assertions.api_assertions.APIAssertions — that module is
deprecated and will be removed. SchemaValidator is the single source of truth.
"""
import json
import structlog
from typing import Any

logger = structlog.get_logger(__name__)


class SchemaValidator:
    def __init__(self, response):
        self.response = response
        try:
            self.body = response.json() if response.content else {}
        except Exception:
            self.body = {}

    # ── Status code assertions ────────────────────────────────────────────────

    def status_is(self, expected: int) -> "SchemaValidator":
        actual = self.response.status_code
        assert actual == expected, (
            f"[SchemaValidator] Status mismatch.\n"
            f"  Expected : {expected}\n"
            f"  Actual   : {actual}\n"
            f"  Body     : {str(self.body)[:300]}"
        )
        logger.debug("assert_status", expected=expected, actual=actual)
        return self

    def status_ok(self) -> "SchemaValidator":
        return self.status_is(200)

    def status_created(self) -> "SchemaValidator":
        return self.status_is(201)

    def status_unauthorized(self) -> "SchemaValidator":
        return self.status_is(401)

    def status_forbidden(self) -> "SchemaValidator":
        return self.status_is(403)

    def status_not_found(self) -> "SchemaValidator":
        return self.status_is(404)

    def status_2xx(self) -> "SchemaValidator":
        actual = self.response.status_code
        assert 200 <= actual < 300, (
            f"[SchemaValidator] Expected 2xx, got {actual}\n"
            f"  Body: {str(self.body)[:300]}"
        )
        return self

    def status_in(self, *codes: int) -> "SchemaValidator":
        actual = self.response.status_code
        assert actual in codes, (
            f"[SchemaValidator] Status {actual} not in expected {set(codes)}\n"
            f"  Body: {str(self.body)[:300]}"
        )
        return self

    def status(self, expected: int) -> "SchemaValidator":
        """Alias for status_is() — supports .status(401) call pattern."""
        return self.status_is(expected)

    # ── Body key assertions ───────────────────────────────────────────────────

    def has_key(self, key: str) -> "SchemaValidator":
        data = self.body.get("data", self.body)
        target = data if isinstance(data, dict) else self.body
        assert key in target, (
            f"[SchemaValidator] Key '{key}' missing in response.\n"
            f"  Available keys: {list(target.keys())}"
        )
        return self

    def has_keys(self, *keys: str) -> "SchemaValidator":
        for key in keys:
            self.has_key(key)
        return self

    def key_equals(self, key: str, expected: Any) -> "SchemaValidator":
        self.has_key(key)
        actual = self.body.get(key)
        assert actual == expected, (
            f"[SchemaValidator] '{key}' value mismatch.\n"
            f"  Expected : {expected}\n"
            f"  Actual   : {actual}"
        )
        return self

    def key_not_null(self, key: str) -> "SchemaValidator":
        data = self.body.get("data", self.body)
        target = data if isinstance(data, dict) else self.body
        assert target.get(key) is not None, (
            f"[SchemaValidator] Key '{key}' is null/missing — expected a value."
        )
        return self

    def key_is_list(self, key: str) -> "SchemaValidator":
        val = self.body.get(key)
        assert isinstance(val, list), (
            f"[SchemaValidator] '{key}' should be a list, got {type(val).__name__}"
        )
        return self

    def key_is_dict(self, key: str) -> "SchemaValidator":
        val = self.body.get(key)
        assert isinstance(val, dict), (
            f"[SchemaValidator] '{key}' should be a dict, got {type(val).__name__}"
        )
        return self

    def list_not_empty(self, key: str) -> "SchemaValidator":
        self.key_is_list(key)
        assert len(self.body[key]) > 0, (
            f"[SchemaValidator] List '{key}' is empty."
        )
        return self

    # ── Auth / token assertions ───────────────────────────────────────────────

    def has_token(self) -> "SchemaValidator":
        """Assert accessToken or token is present and non-empty."""
        data = self.body.get("data", self.body)
        target = data if isinstance(data, dict) else self.body
        token = target.get("accessToken") or target.get("token")
        assert token, (
            f"[SchemaValidator] No token found in response.\n"
            f"  Body: {str(self.body)[:300]}"
        )
        return self

    def no_token(self) -> "SchemaValidator":
        """Assert no token is returned — for failed auth tests."""
        data = self.body.get("data", self.body)
        target = data if isinstance(data, dict) else self.body
        token = target.get("accessToken") or target.get("token")
        assert not token, (
            f"[SchemaValidator] Token should NOT be present but got: {str(token)[:80]}"
        )
        return self

    # ── Error body assertions ─────────────────────────────────────────────────

    def body_contains_error(self, keyword: str) -> "SchemaValidator":
        """Assert error message contains keyword — case-insensitive."""
        raw = str(self.body).lower()
        assert keyword.lower() in raw, (
            f"[SchemaValidator] Error keyword '{keyword}' not found in response.\n"
            f"  Body: {str(self.body)[:300]}"
        )
        return self

    def code_equals(self, expected_code: str) -> "SchemaValidator":
        actual = self.body.get("code", "")
        assert actual == expected_code, (
            f"[SchemaValidator] Response code mismatch.\n"
            f"  Expected : '{expected_code}'\n"
            f"  Actual   : '{actual}'"
        )
        return self

    # ── Performance assertion ─────────────────────────────────────────────────

    def response_time_under(self, ms: int) -> "SchemaValidator":
        elapsed = self.response.elapsed.total_seconds() * 1000
        assert elapsed < ms, (
            f"[SchemaValidator] Response time {elapsed:.0f}ms exceeded {ms}ms SLA."
        )
        logger.debug("assert_response_time", elapsed_ms=round(elapsed), limit_ms=ms)
        return self

    # ── Nested access ─────────────────────────────────────────────────────────

    def nested_key(self, *keys) -> Any:
        """Navigate nested response keys: .nested_key('data', 'user', 'id')"""
        val = self.body
        for k in keys:
            assert isinstance(val, dict) and k in val, (
                f"[SchemaValidator] Nested path "
                f"{'→'.join(str(x) for x in keys)} failed at '{k}'.\n"
                f"  Available: {list(val.keys()) if isinstance(val, dict) else type(val)}"
            )
            val = val[k]
        return val

    # ── Allure attachment ─────────────────────────────────────────────────────

    def attach_to_report(self, name: str = "Response") -> "SchemaValidator":
        """Attach response body to Allure report for visibility on failure."""
        try:
            import allure
            allure.attach(
                json.dumps(self.body, indent=2, default=str),
                name=name,
                attachment_type=allure.attachment_type.JSON,
            )
        except Exception:
            pass
        return self
