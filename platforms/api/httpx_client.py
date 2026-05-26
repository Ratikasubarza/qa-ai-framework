"""
HTTPX Client - blessed async API client for automation tests.

Owns runtime API config, auth injection, request-level headers, timeout policy,
and redacted request logging. Tests should use this public surface instead of
mutating the underlying httpx client directly.
"""
from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any, Optional

import httpx
import structlog

from config.test_config import APIEndpoints, TestConfig, Timeouts
from core.source_intake.security import redact_internal_text

logger = structlog.get_logger(__name__)


class HonoAPIClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
        include_api_key: bool = True,
        headers: Mapping[str, str] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.base_url = (base_url or TestConfig.API_URL).rstrip("/")
        self.api_key = TestConfig.API_KEY if api_key is None else api_key
        self.timeout = timeout or Timeouts.API_REQUEST
        self.include_api_key = include_api_key
        self._token: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._transport = transport
        self._default_headers = {
            "Content-Type": "application/json",
        }
        if self.include_api_key and self.api_key:
            self._default_headers["x-api-key"] = self.api_key
        if headers:
            self._default_headers.update(dict(headers))

    @classmethod
    def no_api_key(cls, **kwargs: Any) -> "HonoAPIClient":
        """Build a client without x-api-key for explicit negative security tests."""
        return cls(include_api_key=False, **kwargs)

    async def __aenter__(self):
        client_kwargs: dict[str, Any] = {
            "base_url": self.base_url,
            "headers": dict(self._default_headers),
            "timeout": self.timeout,
        }
        if self._transport is not None:
            client_kwargs["transport"] = self._transport
        self._client = httpx.AsyncClient(
            **client_kwargs,
        )
        if self._token:
            self._client.headers["Authorization"] = f"Bearer {self._token}"
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    @property
    def token(self) -> str | None:
        return self._token

    def set_auth_token(self, token: str | None) -> "HonoAPIClient":
        """Set or clear the bearer token used by subsequent requests."""
        self._token = token
        if self._client:
            if token:
                self._client.headers["Authorization"] = f"Bearer {token}"
            else:
                self._client.headers.pop("Authorization", None)
        return self

    def clear_auth(self) -> "HonoAPIClient":
        """Clear bearer auth from this client."""
        return self.set_auth_token(None)

    def _require_client(self) -> httpx.AsyncClient:
        if not self._client:
            raise RuntimeError("HonoAPIClient is not started. Use 'async with HonoAPIClient()'.")
        return self._client

    def _merge_headers(
        self,
        headers: Mapping[str, str] | None = None,
        auth_token: str | None = None,
    ) -> dict[str, str] | None:
        merged: dict[str, str] = {}
        if headers:
            merged.update(dict(headers))
        if auth_token:
            merged["Authorization"] = f"Bearer {auth_token}"
        return merged or None

    # Headers whose values must never appear in logs or error messages.
    _SENSITIVE_HEADERS: frozenset[str] = frozenset(
        {"authorization", "x-api-key", "cookie", "set-cookie", "x-auth-token"}
    )

    @staticmethod
    def _redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
        """Return a copy of headers with sensitive values replaced. Safe for logging."""
        sensitive = HonoAPIClient._SENSITIVE_HEADERS
        return {
            k: "[REDACTED]" if k.lower() in sensitive else v
            for k, v in headers.items()
        }

    @staticmethod
    def safe_json(response: httpx.Response) -> dict[str, Any]:
        """Return JSON response content without exposing raw response text."""
        if not response.content:
            return {}
        try:
            data = response.json()
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {"data": data}

    @staticmethod
    def _expected_status_set(expected_status: int | Sequence[int] | None) -> set[int]:
        if expected_status is None:
            return set()
        if isinstance(expected_status, int):
            return {expected_status}
        return {int(status) for status in expected_status}

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Mapping[str, Any] | list[Any] | None = None,
        headers: Mapping[str, str] | None = None,
        auth_token: str | None = None,
        expected_status: int | Sequence[int] | None = None,
    ) -> httpx.Response:
        """Send a request with optional per-call headers and status assertion."""
        client = self._require_client()
        request_id = str(uuid.uuid4())
        tracing_headers: dict[str, str] = {"X-Request-ID": request_id}
        if headers:
            tracing_headers.update(dict(headers))
        response = await client.request(
            method,
            path,
            params=params,
            json=json,
            headers=self._merge_headers(headers=tracing_headers, auth_token=auth_token),
        )
        safe_path = redact_internal_text(path).text
        logger.info(
            "api_request",
            method=method.upper(),
            path=safe_path,
            status=response.status_code,
            request_id=request_id,
        )
        logger.debug(
            "api_request_headers",
            method=method.upper(),
            path=safe_path,
            headers=self._redact_headers(dict(client.headers)),
        )

        expected = self._expected_status_set(expected_status)
        if expected and response.status_code not in expected:
            expected_text = ", ".join(str(status) for status in sorted(expected))
            raise AssertionError(
                f"Expected HTTP status {expected_text} for {method.upper()} {safe_path}, "
                f"got {response.status_code}"
            )
        return response

    async def login(self, email: str, password: str, resource: str | None = None) -> str:
        """Login and store Bearer token. Returns token."""
        payload: dict[str, str] = {"email": email, "password": password}
        if resource:
            payload["resource"] = resource
        response = await self.post(APIEndpoints.LOGIN, json=payload)
        logger.info("api_login", status=response.status_code, resource=resource or "user")
        response.raise_for_status()

        data = self.safe_json(response)
        body = data.get("data", {}) or {}
        token = (
            body.get("accessToken")
            or body.get("token")
            or data.get("accessToken")
            or data.get("token")
        )

        if not token:
            logger.warning("api_login_token_missing", response_keys=list(data.keys()))
            raise ValueError(f"Token not found in login response. Keys: {list(data.keys())}")

        self.set_auth_token(token)
        logger.info("api_login_success", resource=resource or "user")
        return token

    async def get(
        self,
        path: str,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        auth_token: str | None = None,
        expected_status: int | Sequence[int] | None = None,
    ) -> httpx.Response:
        return await self.request(
            "GET",
            path,
            params=params,
            headers=headers,
            auth_token=auth_token,
            expected_status=expected_status,
        )

    async def post(
        self,
        path: str,
        json: Mapping[str, Any] | list[Any] | None = None,
        headers: Mapping[str, str] | None = None,
        auth_token: str | None = None,
        expected_status: int | Sequence[int] | None = None,
    ) -> httpx.Response:
        return await self.request(
            "POST",
            path,
            json=json,
            headers=headers,
            auth_token=auth_token,
            expected_status=expected_status,
        )

    async def put(
        self,
        path: str,
        json: Mapping[str, Any] | list[Any] | None = None,
        headers: Mapping[str, str] | None = None,
        auth_token: str | None = None,
        expected_status: int | Sequence[int] | None = None,
    ) -> httpx.Response:
        return await self.request(
            "PUT",
            path,
            json=json,
            headers=headers,
            auth_token=auth_token,
            expected_status=expected_status,
        )

    async def delete(
        self,
        path: str,
        json: Mapping[str, Any] | list[Any] | None = None,
        headers: Mapping[str, str] | None = None,
        auth_token: str | None = None,
        expected_status: int | Sequence[int] | None = None,
    ) -> httpx.Response:
        return await self.request(
            "DELETE",
            path,
            json=json,
            headers=headers,
            auth_token=auth_token,
            expected_status=expected_status,
        )
