"""Shared fixtures for Auth API tests."""
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


@pytest.fixture(scope="module")
def auth_user(request):
    suffix    = f"{int(time.time())}{random.randint(100, 999)}"
    user      = create_approved_user_sync(suffix=suffix)
    run_id    = os.getenv("RUN_ID", request.module.__name__)
    worker_id = getattr(request.config, "workerinput", {}).get("workerid", "main")

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
    return user


@pytest_asyncio.fixture(scope="module")
async def auth_token(auth_user) -> str:
    async with HonoAPIClient() as client:
        resp = await client.post(APIEndpoints.LOGIN, json={
            "email":    auth_user["email"],
            "password": auth_user["password"],
        })
    skip_on_email_quota(resp)
    data = resp.json()
    body = data.get("data", data)
    token = body.get("accessToken") or body.get("token", "")
    assert token, f"Login failed for auth_user: {data}"
    return token


@pytest_asyncio.fixture(scope="module")
async def auth_refresh_token(auth_user) -> str:
    async with HonoAPIClient() as client:
        resp = await client.post(APIEndpoints.LOGIN, json={
            "email":    auth_user["email"],
            "password": auth_user["password"],
        })
    skip_on_email_quota(resp)
    data = resp.json()
    body = data.get("data", data)
    token = body.get("refreshToken") or body.get("refresh_token", "")
    return token
