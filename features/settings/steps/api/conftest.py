"""Shared fixtures for Settings API tests."""
import time
import random
import pytest

from core.db.test_user_helper import create_approved_user_sync
from core.db.db_client import DBClient
from core.test_data.cleanup_registry import cleanup_registry
from platforms.api.httpx_client import HonoAPIClient
from skills.testing.helpers import skip_on_email_quota
from config.test_config import APIEndpoints


@pytest.fixture(scope="module")
def settings_user(request):
    suffix    = f"{int(time.time())}{random.randint(100, 999)}"
    user      = create_approved_user_sync(suffix=suffix)
    worker_id = getattr(request.config, "workerinput", {}).get("workerid", "main")
    run_id    = request.module.__name__

    def _delete():
        with DBClient() as db:
            db.delete_user(user["user_id"])

    cleanup_registry.register("user", user["user_id"], _delete, run_id=run_id, worker_id=worker_id)
    return user  # cleanup delegated to pytest_sessionfinish via CleanupRegistry


@pytest.fixture(scope="module")
async def settings_token(settings_user) -> str:
    async with HonoAPIClient() as client:
        resp = await client.post(APIEndpoints.LOGIN, json={
            "email":    settings_user["email"],
            "password": settings_user["password"],
        })
    skip_on_email_quota(resp)
    data = resp.json()
    body = data.get("data", data)
    token = body.get("accessToken") or body.get("token", "")
    assert token, f"Login failed for settings_user: {data}"
    return token
