"""Shared fixtures for Privacy API tests — two users required."""
import time
import random
import pytest
import pytest_asyncio

from core.db.test_user_helper import create_approved_user_sync
from platforms.api.httpx_client import HonoAPIClient
from skills.testing.helpers import skip_on_email_quota
from config.test_config import APIEndpoints


@pytest.fixture(scope="function")
def actor_user():
    """The user performing follow/block/mute actions."""
    suffix = f"{int(time.time())}{random.randint(100, 999)}"
    return create_approved_user_sync(suffix=suffix)


@pytest.fixture(scope="function")
def target_user():
    """The user being followed/blocked/muted."""
    suffix = f"{int(time.time()) + 1}{random.randint(100, 999)}"
    return create_approved_user_sync(suffix=suffix)


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
