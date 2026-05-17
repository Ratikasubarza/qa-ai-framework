"""
AuthHelper — single source of truth for all auth operations in tests.
Never hardcode credentials — always read from env via TestConfig or config.
"""
import httpx
import structlog

from config.test_config import TestConfig, APIEndpoints
from config.test_data import KnownAccounts

logger = structlog.get_logger(__name__)

_INVALID_TOKEN = "invalid.token.placeholder"
_EXPIRED_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJleHBpcmVkIiwiZXhwIjoxfQ.invalid"


class AuthError(Exception):
    """Raised when an auth operation fails (login rejected, token missing, network error)."""


def _extract_token(data: dict) -> str | None:
    """Extract accessToken/token from login response, handling nested data key."""
    body = data.get("data", data) or {}
    return body.get("accessToken") or body.get("token")


class AuthHelper:
    """
    Single source of truth for all auth operations in tests.
    Never hardcode credentials — always read from env via TestConfig.
    """

    @classmethod
    def get_user_token(cls, email: str = None, password: str = None) -> str:
        """
        Login and return Bearer token.
        Uses STAGING_EMAIL + STAGING_PASSWORD from .env if not provided.
        Raises: AuthError if login fails.
        """
        email    = email    or KnownAccounts.STAGING_EMAIL
        password = password or KnownAccounts.STAGING_PASSWORD

        if not email or not password:
            raise AuthError(
                "STAGING_EMAIL and STAGING_PASSWORD must be set in .env for user token"
            )

        try:
            resp = httpx.post(
                f"{TestConfig.API_URL}{APIEndpoints.LOGIN}",
                json={"email": email, "password": password},
                headers={"x-api-key": TestConfig.API_KEY, "Content-Type": "application/json"},
                timeout=30,
            )
            logger.info("auth_user_login", status=resp.status_code, email=email)
            if resp.status_code != 200:
                raise AuthError(
                    f"Login failed for {email}: HTTP {resp.status_code} — {resp.text[:200]}"
                )
            token = _extract_token(resp.json())
            if not token:
                raise AuthError(f"Token not found in login response: {list(resp.json().keys())}")
            logger.info("auth_user_token_ok", email=email)
            return token
        except httpx.HTTPError as exc:
            raise AuthError(f"HTTP error during user login: {exc}") from exc

    @classmethod
    def get_cms_token(cls) -> str:
        """
        CMS admin token.
        Uses STAGING_CMS_EMAIL + STAGING_CMS_PASSWORD from .env.
        Raises: AuthError if login fails.
        """
        email    = KnownAccounts.CMS_EMAIL
        password = KnownAccounts.CMS_PASSWORD

        if not email or not password:
            raise AuthError(
                "STAGING_CMS_EMAIL and STAGING_CMS_PASSWORD must be set in .env for CMS token"
            )

        try:
            resp = httpx.post(
                f"{TestConfig.API_URL}{APIEndpoints.LOGIN}",
                json={"email": email, "password": password, "resource": "admin"},
                headers={"x-api-key": TestConfig.API_KEY, "Content-Type": "application/json"},
                timeout=30,
            )
            logger.info("auth_cms_login", status=resp.status_code)
            if resp.status_code != 200:
                raise AuthError(
                    f"CMS login failed: HTTP {resp.status_code} — {resp.text[:200]}"
                )
            token = _extract_token(resp.json())
            if not token:
                raise AuthError(f"CMS token not found in response: {list(resp.json().keys())}")
            logger.info("auth_cms_token_ok")
            return token
        except httpx.HTTPError as exc:
            raise AuthError(f"HTTP error during CMS login: {exc}") from exc

    @classmethod
    def get_invalid_token(cls) -> str:
        """Return a known-invalid Bearer token for negative tests."""
        return _INVALID_TOKEN

    @classmethod
    def get_expired_token(cls) -> str:
        """Return a known-expired Bearer token for negative tests."""
        return _EXPIRED_TOKEN

    @classmethod
    async def create_and_approve_user(cls) -> dict:
        """
        Full user setup flow: Register → verify DB → CMS approve → login.
        Returns {email, password, user_id, status, fullname, token}.
        Wraps core/db/test_user_helper — does not duplicate its logic.
        """
        from core.db.test_user_helper import create_approved_user
        user  = await create_approved_user()
        token = cls.get_user_token(email=user["email"], password=user["password"])
        return {**user, "token": token}

    @classmethod
    def build_auth_header(cls, token: str) -> dict:
        """Return {"Authorization": "Bearer {token}"}."""
        return {"Authorization": f"Bearer {token}"}

    @classmethod
    def build_cms_auth_header(cls) -> dict:
        """Return CMS admin auth header — calls get_cms_token() internally."""
        return cls.build_auth_header(cls.get_cms_token())
