"""Shared fixtures for Search API tests."""
import os
import time
import random

import pytest
import structlog

from conftest_shared_fixtures import (  # noqa: F401 — re-export for pytest fixture discovery
    auth_token,
    registered_user,
)
from config.test_config import APIEndpoints
from core.db.db_client import DBClient
from core.db.test_user_helper import create_approved_user_sync
from core.test_data.cleanup_registry import cleanup_registry
from platforms.api.httpx_client import HonoAPIClient
from skills.testing.helpers import skip_on_email_quota

logger = structlog.get_logger(__name__)


def _run_id(request) -> str:
    return os.getenv("RUN_ID", request.module.__name__)


def _worker_id(request) -> str:
    try:
        return request.config.workerinput.get("workerid", "main")
    except AttributeError:
        return "main"


# ── Existing fixtures (preserved) ─────────────────────────────────────────────

@pytest.fixture(scope="module")
def search_user():
    suffix = f"{int(time.time())}{random.randint(100, 999)}"
    return create_approved_user_sync(suffix=suffix)


@pytest.fixture(scope="module")
async def search_token(search_user) -> str:
    async with HonoAPIClient() as client:
        resp = await client.post(APIEndpoints.LOGIN, json={
            "email":    search_user["email"],
            "password": search_user["password"],
        })
    skip_on_email_quota(resp)
    data = resp.json()
    body = data.get("data", data)
    token = body.get("accessToken") or body.get("token", "")
    assert token, f"Login failed for search_user: {data}"
    return token


# ── New fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def search_target_profiles(request):
    """
    Creates 6 approved users to use as search targets.
    Needed for FIFO eviction test (TC-RS-009) which requires 6 distinct profiles.
    Cleanup is registered in CleanupRegistry (sync DB delete — safe in session teardown).
    Returns: list of 6 user_id strings
    """
    run_id = _run_id(request)
    worker_id = _worker_id(request)

    profiles = []
    for _ in range(6):
        user = create_approved_user_sync()
        user_id = user["user_id"]
        profiles.append(user_id)

        def _delete(uid=user_id):
            with DBClient() as db:
                db.delete_user(uid)

        cleanup_registry.register(
            entity_type="user",
            entity_id=user_id,
            cleanup_fn=_delete,
            run_id=run_id,
            worker_id=worker_id,
        )

    logger.info("fixture_search_targets_created", count=len(profiles))
    return profiles  # cleanup delegated to pytest_sessionfinish via CleanupRegistry


@pytest.fixture(scope="module", autouse=False)
async def clean_recent_searches(auth_token):
    """
    Clears the authenticated user's recent search history before and after the module.
    autouse=False — only applied to tests that explicitly request this fixture.

    Usage: include 'clean_recent_searches' in the test function signature
    when a fresh recent-search state is required.
    """
    async def _clear(token: str) -> None:
        async with HonoAPIClient() as client:
            client.set_auth_token(token)
            resp = await client.get(APIEndpoints.SEARCH_RECENT)
            if resp.status_code == 200:
                entries = (resp.json().get("data") or [])
                for entry in entries:
                    entry_id = entry.get("id")
                    if entry_id:
                        await client.delete(
                            APIEndpoints.search_recent_delete(entry_id)
                        )

    await _clear(auth_token)
    yield
    await _clear(auth_token)
