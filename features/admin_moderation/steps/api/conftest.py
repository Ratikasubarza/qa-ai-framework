"""
Feature-level fixtures for Admin Moderation API tests.

Depends on shared auth chain from conftest.shared_fixtures (registered globally
via pytest_plugins in root conftest.py). Re-imported here to make dependencies explicit.

Fixtures:
    admin_token            — admin Bearer JWT (from KnownAccounts.ADMIN_TOKEN env var)
    regular_user_token     — non-admin Bearer JWT (for 403 security tests)
    pending_reported_post  — post in PENDING report state (owned by second_user)
    hidden_reported_post   — independent post in HIDDEN state (separate resource, no coupling)
"""
import os

import pytest
import structlog

from conftest_shared_fixtures import (  # noqa: F401 — re-export for pytest fixture discovery
    admin_client,
    admin_user,
    auth_token,
    authenticated_client,
    registered_user,
    second_user,
    second_user_token,
)
from config.test_config import APIEndpoints
from features.posts.test_data.create_post_test_data import CreatePostPayload
from platforms.api.httpx_client import HonoAPIClient

logger = structlog.get_logger(__name__)


# ── admin_token ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def admin_token(admin_user) -> str:
    """Admin Bearer JWT. Delegates fail-fast check to admin_user fixture."""
    return admin_user["token"]


# ── regular_user_token ────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def regular_user_token(auth_token) -> str:
    """Non-admin user token — used to verify 403 on admin-only endpoints."""
    return auth_token


def _run_id(request) -> str:
    return os.getenv("RUN_ID", request.module.__name__)


def _worker_id(request) -> str:
    try:
        return request.config.workerinput.get("workerid", "main")
    except AttributeError:
        return "main"


# ── pending_reported_post ─────────────────────────────────────────────────────

@pytest.fixture(scope="module")
async def pending_reported_post(second_user_token, auth_token, request):
    """
    A post with a PENDING report. Admin moderation tests start from this state.

    Setup flow:
      1. second_user creates a post (they are the content owner)
      2. registered_user (auth_token) submits a report on it → post enters admin queue

    Returns: str (post_id)
    Teardown: best-effort DELETE by second_user after module completes.
    """
    async with HonoAPIClient() as client:
        client.set_auth_token(second_user_token)
        resp = await client.post(
            APIEndpoints.POSTS,
            json=CreatePostPayload.valid().as_dict(),
        )

    assert resp.status_code in (200, 201), (
        f"pending_reported_post creation failed: {resp.status_code} — {resp.text[:200]}"
    )
    body = resp.json()
    post_id = (body.get("data") or body).get("id", "")
    assert post_id, f"No post id in response: {body}"

    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        report_resp = await client.post(
            APIEndpoints.post_report(post_id),
            json={"category": "SPAM"},
        )

    assert report_resp.status_code in (200, 201), (
        f"Report submission failed: {report_resp.status_code} — {report_resp.text[:200]}"
    )

    logger.info(
        "fixture_pending_report_created",
        fixture="pending_reported_post",
        post_id=post_id,
        report_status="PENDING",
    )

    yield post_id

    try:
        async with HonoAPIClient() as client:
            client.set_auth_token(second_user_token)
            await client.delete(APIEndpoints.post_detail(post_id))
    except Exception:
        pass


# ── hidden_reported_post ──────────────────────────────────────────────────────

@pytest.fixture(scope="module")
async def hidden_reported_post(second_user_token, auth_token, admin_client, request):
    """
    An independent post already in HIDDEN state.

    Uses a separate post from pending_reported_post so tests using either fixture
    can coexist in the same module without state interference.

    Setup flow:
      1. second_user creates a post
      2. registered_user reports it → PENDING
      3. admin hides it → HIDDEN

    Returns: str (post_id)
    Teardown: best-effort DELETE by second_user after module completes.
    """
    async with HonoAPIClient() as client:
        client.set_auth_token(second_user_token)
        resp = await client.post(
            APIEndpoints.POSTS,
            json=CreatePostPayload.valid().as_dict(),
        )

    assert resp.status_code in (200, 201), (
        f"hidden_reported_post creation failed: {resp.status_code} — {resp.text[:200]}"
    )
    body = resp.json()
    post_id = (body.get("data") or body).get("id", "")
    assert post_id, f"No post id in response: {body}"

    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        report_resp = await client.post(
            APIEndpoints.post_report(post_id),
            json={"category": "SPAM"},
        )

    assert report_resp.status_code in (200, 201), (
        f"hidden_reported_post report failed: {report_resp.status_code} — {report_resp.text[:200]}"
    )

    hide_resp = await admin_client.post(APIEndpoints.post_hide(post_id))
    # 422 = already hidden — treat as idempotent success
    assert hide_resp.status_code in (200, 422), (
        f"Admin hide failed: {hide_resp.status_code} — {hide_resp.text[:200]}"
    )

    logger.info(
        "fixture_post_hidden",
        fixture="hidden_reported_post",
        post_id=post_id,
        status="HIDDEN",
    )

    yield post_id

    try:
        async with HonoAPIClient() as client:
            client.set_auth_token(second_user_token)
            await client.delete(APIEndpoints.post_detail(post_id))
    except Exception:
        pass
