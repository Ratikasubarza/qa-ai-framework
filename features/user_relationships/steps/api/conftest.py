"""
Feature-level fixtures for User Relationships API tests.

Fixture chain:
    registered_user → auth_token → authenticated_client  (from shared_fixtures plugin)
    follow_target   — a distinct approved user that registered_user can follow
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


# ── follow_target ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def follow_target(request):
    """
    A fully approved staging user that registered_user can follow.
    Returns: str (user_id)
    Cleanup: delegated to CleanupRegistry at session end.
    """
    run_id = _run_id(request)
    worker_id = _worker_id(request)

    user = create_approved_user_sync()
    uid = user["user_id"]

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

    logger.info("fixture_user_created", fixture="follow_target", user_id=uid)
    yield uid
