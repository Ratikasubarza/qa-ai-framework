"""Shared fixtures for Auth API tests."""
import time
import random
import pytest
import pytest_asyncio

from core.db.test_user_helper import create_approved_user_sync
from platforms.api.httpx_client import HonoAPIClient
from skills.testing.helpers import skip_on_email_quota
from config.test_config import APIEndpoints


@pytest.fixture(scope="function")
def auth_user():
    suffix = f"{int(time.time())}{random.randint(100, 999)}"
    return create_approved_user_sync(suffix=suffix)


@pytest_asyncio.fixture(scope="function")
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


@pytest_asyncio.fixture(scope="function")
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
