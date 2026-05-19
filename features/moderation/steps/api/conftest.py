"""Shared fixtures for Moderation API tests."""
import time
import random
import pytest
import pytest_asyncio

from core.db.test_user_helper import create_approved_user_sync
from platforms.api.httpx_client import HonoAPIClient
from skills.testing.helpers import skip_on_email_quota
from config.test_config import APIEndpoints
from features.posts.test_data.create_post_test_data import CreatePostPayload


@pytest.fixture(scope="module")
def mod_user():
    suffix = f"{int(time.time())}{random.randint(100, 999)}"
    return create_approved_user_sync(suffix=suffix)


@pytest_asyncio.fixture(scope="module")
async def mod_token(mod_user) -> str:
    async with HonoAPIClient() as client:
        resp = await client.post(APIEndpoints.LOGIN, json={
            "email":    mod_user["email"],
            "password": mod_user["password"],
        })
    skip_on_email_quota(resp)
    data = resp.json()
    body = data.get("data", data)
    token = body.get("accessToken") or body.get("token", "")
    assert token, f"Login failed for mod_user: {data}"
    return token


@pytest_asyncio.fixture(scope="module")
async def mod_post_id(mod_token) -> str:
    async with HonoAPIClient() as client:
        resp = await client.post(
            APIEndpoints.POSTS,
            json=CreatePostPayload.valid().as_dict(),
            headers={"Authorization": f"Bearer {mod_token}"},
        )
    assert resp.status_code in (200, 201), f"Post creation failed: {resp.text[:200]}"
    body = resp.json()
    data = body.get("data", body)
    post_id = data.get("id", "")
    assert post_id, f"No post id: {body}"
    return post_id
