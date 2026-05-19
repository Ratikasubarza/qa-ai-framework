"""Shared fixtures for Posts API tests."""
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
def post_user():
    """
    Create one approved user per test module — reused across all post tests.
    Scope=module keeps DB writes to a minimum.
    """
    suffix = f"{int(time.time())}{random.randint(100, 999)}"
    return create_approved_user_sync(suffix=suffix)


@pytest_asyncio.fixture(scope="module")
async def post_token(post_user) -> str:
    """Login once per module and return bearer token."""
    async with HonoAPIClient() as client:
        resp = await client.post(APIEndpoints.LOGIN, json={
            "email":    post_user["email"],
            "password": post_user["password"],
        })
    skip_on_email_quota(resp)
    data = resp.json()
    body = data.get("data", data)
    token = body.get("accessToken") or body.get("token", "")
    assert token, f"Login failed for post_user: {data}"
    return token


@pytest_asyncio.fixture(scope="module")
async def created_post_id(post_token) -> str:
    """Create one post per module — reused for GET/PUT/DELETE/visibility tests."""
    async with HonoAPIClient() as client:
        resp = await client.post(
            APIEndpoints.POSTS,
            json=CreatePostPayload.valid().as_dict(),
            headers={"Authorization": f"Bearer {post_token}"},
        )
    assert resp.status_code in (200, 201), f"Post creation failed: {resp.text[:200]}"
    body = resp.json()
    data = body.get("data", body)
    post_id = data.get("id", "")
    assert post_id, f"No post id in response: {body}"
    return post_id
