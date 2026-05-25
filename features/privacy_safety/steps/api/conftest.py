"""
Feature-level fixtures for Privacy Safety API tests.

Fixture chain:
    registered_user → auth_token → authenticated_client  (from shared_fixtures plugin)
    target_users    — 2 pre-approved staging users for block/mute target operations
    cleanup_block_mute_state  — autouse, module-scoped, wipes block/mute state before and after
"""
import os

import pytest
import structlog

from config.test_config import APIEndpoints
from core.db.db_client import DBClient
from core.db.test_user_helper import create_approved_user_sync
from core.test_data.cleanup_registry import cleanup_registry
from platforms.api.httpx_client import HonoAPIClient

logger = structlog.get_logger(__name__)


def _run_id(request) -> str:
    return os.getenv("RUN_ID", request.module.__name__)


def _worker_id(request) -> str:
    try:
        return request.config.workerinput.get("workerid", "main")
    except AttributeError:
        return "main"


# ── target_users ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def target_users(request):
    """
    Creates 2 fully approved staging users for block/mute target operations.
    Returns: list[str] — 2 user_id strings.
    Cleanup: delegated to CleanupRegistry at session end.
    """
    run_id = _run_id(request)
    worker_id = _worker_id(request)
    user_ids: list[str] = []

    for _ in range(2):
        user = create_approved_user_sync()
        uid = user["user_id"]
        user_ids.append(uid)

        def _delete(uid=uid):
            with DBClient() as db:
                db.delete_user(uid)

        cleanup_registry.register(
            entity_type="user",
            entity_id=uid,
            cleanup_fn=_delete,
            run_id=run_id,
            worker_id=worker_id,
        )
        logger.info("fixture_user_created", fixture="target_users", user_id=uid)

    return user_ids


# ── cleanup_block_mute_state ──────────────────────────────────────────────────

@pytest.fixture(scope="module", autouse=True)
async def cleanup_block_mute_state(authenticated_client, target_users):
    """
    Wipes block/mute state for all target_users before and after the module.
    Prevents state bleed between runs and CI reruns on the persistent staging DB.
    """
    async def _clear() -> None:
        for endpoint in (
            APIEndpoints.SETTINGS_ACCOUNTS_BLOCK,
            APIEndpoints.SETTINGS_ACCOUNTS_MUTE,
        ):
            try:
                await authenticated_client.delete(
                    endpoint, json={"target_user_ids": target_users}
                )
            except Exception:
                pass

    await _clear()
    yield
    await _clear()
