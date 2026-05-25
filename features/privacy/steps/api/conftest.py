"""Shared fixtures for Privacy API tests — two users required.

Deliberately kept at scope="function": tests mutate relationship state
(follow → block sequence), and each test requires a clean pair.
CleanupRegistry ensures orphaned users are deleted at session end.
"""
import os
import time
import random
import pytest
import pytest_asyncio

from core.db.db_client import DBClient
from core.db.test_user_helper import create_approved_user_sync
from core.test_data.cleanup_registry import cleanup_registry
from platforms.api.httpx_client import HonoAPIClient
from skills.testing.helpers import skip_on_email_quota
from config.test_config import APIEndpoints


def _register_cleanup(user: dict, run_id: str, worker_id: str) -> None:
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


@pytest.fixture(scope="function")
def actor_user(request):
    """The user performing follow/block/mute actions."""
    suffix    = f"{int(time.time())}{random.randint(100, 999)}"
    user      = create_approved_user_sync(suffix=suffix)
    run_id    = os.getenv("RUN_ID", request.module.__name__)
    worker_id = getattr(request.config, "workerinput", {}).get("workerid", "main")
    _register_cleanup(user, run_id, worker_id)
    return user


@pytest.fixture(scope="function")
def target_user(request):
    """The user being followed/blocked/muted."""
    suffix    = f"{int(time.time()) + 1}{random.randint(100, 999)}"
    user      = create_approved_user_sync(suffix=suffix)
    run_id    = os.getenv("RUN_ID", request.module.__name__)
    worker_id = getattr(request.config, "workerinput", {}).get("workerid", "main")
    _register_cleanup(user, run_id, worker_id)
    return user


@pytest_asyncio.fixture(scope="function")
async def actor_token(actor_user) -> str:
    async with HonoAPIClient() as client:
        resp = await client.post(APIEndpoints.LOGIN, json={
            "email":    actor_user["email"],
            "password": actor_user["password"],
        })
    skip_on_email_quota(resp)
    data = resp.json()
    body = data.get("data", data)
    token = body.get("accessToken") or body.get("token", "")
    assert token, f"Login failed for actor_user: {data}"
    return token
