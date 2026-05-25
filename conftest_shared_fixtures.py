"""
Shared auth and data fixture chain — canonical fixtures for all API/web tests.

Loaded as a pytest plugin via pytest_plugins in root conftest.py.
Do NOT import from this module directly — pytest discovers fixtures automatically.

Fixture dependency chain:
    registered_user  →  auth_token        →  authenticated_client
    second_user      →  second_user_token
    admin_user                             →  admin_client
"""
import os

import pytest
import structlog

from config.test_config import APIEndpoints
from config.test_data import KnownAccounts
from core.db.db_client import DBClient
from core.db.test_user_helper import create_approved_user_sync
from core.test_data.cleanup_registry import cleanup_registry
from platforms.api.httpx_client import HonoAPIClient

logger = structlog.get_logger(__name__)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _run_id(request) -> str:
    return os.getenv("RUN_ID", "pytest")


def _worker_id(request) -> str:
    try:
        return request.config.workerinput.get("workerid", "main")
    except AttributeError:
        return "main"


def _register_user_cleanup(user: dict, run_id: str, worker_id: str) -> None:
    """Register user deletion in CleanupRegistry immediately after creation."""
    user_id = user["user_id"]

    def _delete():
        with DBClient() as db:
            db.delete_user(user_id)

    cleanup_registry.register(
        entity_type="user",
        entity_id=user_id,
        cleanup_fn=_delete,
        run_id=run_id,
        worker_id=worker_id,
    )


def _extract_token(resp_json: dict) -> str:
    """Extract token from login response — handles both accessToken and token shapes."""
    body = resp_json.get("data", resp_json) or {}
    return body.get("accessToken") or body.get("token") or ""


# ── FIXTURE 1: registered_user ────────────────────────────────────────────────

@pytest.fixture(scope="module")
def registered_user(request):
    """
    Creates a fully approved user in staging DB.
    Returns dict: {email, password, user_id, status, fullname}
    Teardown is delegated to CleanupRegistry — runs at session end.
    """
    run_id = _run_id(request)
    worker_id = _worker_id(request)

    user = create_approved_user_sync()

    logger.info(
        "fixture_user_created",
        fixture="registered_user",
        user_id=user["user_id"],
        worker_id=worker_id,
    )

    _register_user_cleanup(user, run_id, worker_id)
    yield user


# ── FIXTURE 2: admin_user ─────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def admin_user():
    """
    Returns admin credentials from env.
    Fails fast with a clear message if TEST_ADMIN_TOKEN is not set.
    Does NOT create a DB user — uses the pre-existing staging admin account.
    """
    token = KnownAccounts.ADMIN_TOKEN
    assert token, (
        "TEST_ADMIN_TOKEN env var is not set. "
        "Set it in .env to an admin-role JWT from the dev environment. "
        "Never commit the actual token value."
    )
    return {"token": token, "role": "admin"}


# ── FIXTURE 3: auth_token ─────────────────────────────────────────────────────

@pytest.fixture(scope="module")
async def auth_token(registered_user):
    """
    Performs POST /v1/users/login with registered_user credentials.
    Returns: str (Bearer token)

    Login is done via API (not DB bypass) to exercise the actual auth stack
    and ensure the token has correct expiry and claims.
    """
    async with HonoAPIClient() as client:
        resp = await client.post(
            APIEndpoints.LOGIN,
            json={
                "email":    registered_user["email"],
                "password": registered_user["password"],
            },
        )

    assert resp.status_code == 200, (
        f"Login fixture failed: {resp.status_code} — {resp.text[:200]}. "
        "Check HONO_API_URL, HONO_API_KEY, and that registered_user was approved."
    )
    token = _extract_token(resp.json())
    assert token, f"Login response returned empty token. Body: {resp.text[:200]}"
    return token


# ── FIXTURE 4: authenticated_client ──────────────────────────────────────────

@pytest.fixture(scope="module")
async def authenticated_client(auth_token):
    """
    Yields a pre-authenticated HonoAPIClient.
    Most API tests should request this fixture instead of constructing their own client.

    Usage:
        async def test_something(authenticated_client):
            resp = await authenticated_client.get(APIEndpoints.ME)
    """
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        yield client


# ── FIXTURE 5: admin_client ───────────────────────────────────────────────────

@pytest.fixture(scope="module")
async def admin_client(admin_user):
    """
    Yields a pre-authenticated HonoAPIClient with admin token.
    For tests that hit CMS endpoints (/v1/users/:id/approve, /v1/users, etc.).
    """
    async with HonoAPIClient() as client:
        client.set_auth_token(admin_user["token"])
        yield client


# ── FIXTURE 6: second_user ────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def second_user(request):
    """
    A second distinct approved user for cross-user test scenarios.
    Example: user B reports a post owned by user A.
    Returns dict: {email, password, user_id, status, fullname}
    """
    run_id = _run_id(request)
    worker_id = _worker_id(request)

    user = create_approved_user_sync()

    logger.info(
        "fixture_user_created",
        fixture="second_user",
        user_id=user["user_id"],
        worker_id=worker_id,
    )

    _register_user_cleanup(user, run_id, worker_id)
    yield user


# ── FIXTURE 7: second_user_token ─────────────────────────────────────────────

@pytest.fixture(scope="module")
async def second_user_token(second_user):
    """Bearer token for the second test user."""
    async with HonoAPIClient() as client:
        resp = await client.post(
            APIEndpoints.LOGIN,
            json={
                "email":    second_user["email"],
                "password": second_user["password"],
            },
        )
    assert resp.status_code == 200, (
        f"second_user login failed: {resp.status_code} — {resp.text[:200]}"
    )
    token = _extract_token(resp.json())
    assert token, f"second_user login returned empty token. Body: {resp.text[:200]}"
    return token
