"""
Feature-level fixtures for Post Interactions API tests.

Fixture chain:
    regular_user    — acting user (reporter / viewer / not-interested marker); includes login token
    reported_post   — post owned by a separate user that regular_user can report
    hidden_post     — post hidden by admin (requires TEST_ADMIN_TOKEN; skips if unset)
"""
import os

import pytest
import structlog

from config.test_config import APIEndpoints
from config.test_data import KnownAccounts
from core.db.db_client import DBClient
from core.db.test_user_helper import create_approved_user_sync
from core.test_data.cleanup_registry import cleanup_registry
from features.posts.test_data.create_post_test_data import CreatePostPayload
from platforms.api.httpx_client import HonoAPIClient

logger = structlog.get_logger(__name__)


def _run_id(request) -> str:
    return os.getenv("RUN_ID", request.module.__name__)


def _worker_id(request) -> str:
    try:
        return request.config.workerinput.get("workerid", "main")
    except AttributeError:
        return "main"


def _register_user_cleanup(user: dict, run_id: str, worker_id: str) -> None:
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
    body = resp_json.get("data", resp_json) or {}
    return body.get("accessToken") or body.get("token") or ""


# ── regular_user ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
async def regular_user(request):
    """
    Acting user for all post-interaction tests.
    Returns: dict with create_approved_user_sync keys plus "token" (Bearer JWT).
    Cleanup: delegated to CleanupRegistry at session end.
    """
    run_id = _run_id(request)
    worker_id = _worker_id(request)

    user = create_approved_user_sync()
    _register_user_cleanup(user, run_id, worker_id)

    async with HonoAPIClient() as client:
        resp = await client.post(
            APIEndpoints.LOGIN,
            json={"email": user["email"], "password": user["password"]},
        )
    assert resp.status_code == 200, (
        f"regular_user login failed: {resp.status_code} — {resp.text[:200]}"
    )
    token = _extract_token(resp.json())
    assert token, f"regular_user login returned empty token. Body: {resp.text[:200]}"

    logger.info("fixture_user_created", fixture="regular_user", user_id=user["user_id"])
    return {**user, "token": token}


# ── reported_post ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
async def reported_post(regular_user, request):
    """
    A post owned by a separate user that regular_user can report.
    Post owner is created internally and registered for CleanupRegistry.
    Returns: str (post_id)
    Teardown: best-effort DELETE of post after module.
    """
    run_id = _run_id(request)
    worker_id = _worker_id(request)

    post_owner = create_approved_user_sync()
    _register_user_cleanup(post_owner, run_id, worker_id)

    async with HonoAPIClient() as client:
        login_resp = await client.post(
            APIEndpoints.LOGIN,
            json={"email": post_owner["email"], "password": post_owner["password"]},
        )
    assert login_resp.status_code == 200, (
        f"reported_post owner login failed: {login_resp.status_code} — {login_resp.text[:200]}"
    )
    owner_token = _extract_token(login_resp.json())
    assert owner_token, f"post_owner login returned empty token. Body: {login_resp.text[:200]}"

    async with HonoAPIClient() as client:
        client.set_auth_token(owner_token)
        create_resp = await client.post(
            APIEndpoints.POSTS,
            json=CreatePostPayload.valid().as_dict(),
        )
    assert create_resp.status_code in (200, 201), (
        f"reported_post creation failed: {create_resp.status_code} — {create_resp.text[:200]}"
    )
    body = create_resp.json()
    post_id = (body.get("data") or body).get("id", "")
    assert post_id, f"No post id in reported_post response: {body}"

    logger.info("fixture_post_created", fixture="reported_post", post_id=post_id)
    yield post_id

    try:
        async with HonoAPIClient() as client:
            client.set_auth_token(owner_token)
            await client.delete(APIEndpoints.post_detail(post_id))
    except Exception:
        pass


# ── hidden_post ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
async def hidden_post(regular_user, request):
    """
    A post hidden by admin — tests interactions with admin-hidden content.
    Skips the entire module if TEST_ADMIN_TOKEN is not set.
    Returns: str (post_id)
    Teardown: best-effort DELETE of post after module.
    """
    if not KnownAccounts.ADMIN_TOKEN:
        pytest.skip("TEST_ADMIN_TOKEN not set — skipping hidden_post-dependent tests")

    run_id = _run_id(request)
    worker_id = _worker_id(request)

    post_owner = create_approved_user_sync()
    _register_user_cleanup(post_owner, run_id, worker_id)

    async with HonoAPIClient() as client:
        login_resp = await client.post(
            APIEndpoints.LOGIN,
            json={"email": post_owner["email"], "password": post_owner["password"]},
        )
    assert login_resp.status_code == 200, (
        f"hidden_post owner login failed: {login_resp.status_code} — {login_resp.text[:200]}"
    )
    owner_token = _extract_token(login_resp.json())
    assert owner_token, f"post_owner login returned empty token. Body: {login_resp.text[:200]}"

    async with HonoAPIClient() as client:
        client.set_auth_token(owner_token)
        create_resp = await client.post(
            APIEndpoints.POSTS,
            json=CreatePostPayload.valid().as_dict(),
        )
    assert create_resp.status_code in (200, 201), (
        f"hidden_post creation failed: {create_resp.status_code} — {create_resp.text[:200]}"
    )
    body = create_resp.json()
    post_id = (body.get("data") or body).get("id", "")
    assert post_id, f"No post id in hidden_post response: {body}"

    async with HonoAPIClient() as client:
        client.set_auth_token(regular_user["token"])
        report_resp = await client.post(
            APIEndpoints.post_report(post_id),
            json={"reason": "spam"},
        )
    assert report_resp.status_code in (200, 201), (
        f"hidden_post report step failed: {report_resp.status_code} — {report_resp.text[:200]}"
    )

    async with HonoAPIClient() as client:
        client.set_auth_token(KnownAccounts.ADMIN_TOKEN)
        hide_resp = await client.post(APIEndpoints.post_hide(post_id))
    assert hide_resp.status_code in (200, 201), (
        f"hidden_post admin-hide step failed: {hide_resp.status_code} — {hide_resp.text[:200]}"
    )

    logger.info("fixture_post_hidden", fixture="hidden_post", post_id=post_id)
    yield post_id

    try:
        async with HonoAPIClient() as client:
            client.set_auth_token(owner_token)
            await client.delete(APIEndpoints.post_detail(post_id))
    except Exception:
        pass
