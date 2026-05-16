"""Shared fixtures for CMS users API tests."""
import pytest_asyncio

from features.cms_login.test_data.cms_login_test_data import CmsLoginTestData
from platforms.api.httpx_client import HonoAPIClient
from config.test_config import APIEndpoints


@pytest_asyncio.fixture
async def cms_token() -> str:
    """Get a fresh CMS admin bearer token for every test that needs it."""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.LOGIN,
            json=CmsLoginTestData.valid_payload(),
        )
    data = response.json()
    body = data.get("data", data)
    return body.get("accessToken") or body.get("token", "")
