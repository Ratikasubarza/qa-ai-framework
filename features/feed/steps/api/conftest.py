"""Shared fixtures for Feed API tests."""
import time
import random
import pytest

from config.test_config import APIEndpoints
from config.test_data import KnownAccounts
from core.db.test_user_helper import create_approved_user_sync
from platforms.api.httpx_client import HonoAPIClient
from skills.testing.helpers import skip_on_email_quota


def _extract_token(resp_json: dict) -> str:
    body = resp_json.get("data", resp_json) or {}
    return body.get("accessToken") or body.get("token") or ""


@pytest.fixture(scope="module")
def feed_user():
    suffix = f"{int(time.time())}{random.randint(100, 999)}"
    return create_approved_user_sync(suffix=suffix)


@pytest.fixture(scope="module")
async def feed_token(feed_user) -> str:
    async with HonoAPIClient() as client:
        resp = await client.post(APIEndpoints.LOGIN, json={
            "email":    feed_user["email"],
            "password": feed_user["password"],
        })
    skip_on_email_quota(resp)
    data = resp.json()
    token = _extract_token(data)
    assert token, f"Login failed for feed_user: {data}"
    return token


@pytest.fixture(scope="module")
async def staging_token() -> str:
    """Login with the known staging account (STAGING_EMAIL / STAGING_PASSWORD from .env)."""
    email    = KnownAccounts.STAGING_EMAIL
    password = KnownAccounts.STAGING_PASSWORD
    assert email and password, (
        "STAGING_EMAIL and STAGING_PASSWORD must be set in .env"
    )
    async with HonoAPIClient() as client:
        resp = await client.post(APIEndpoints.LOGIN, json={
            "email":    email,
            "password": password,
        })
    skip_on_email_quota(resp)
    data = resp.json()
    token = _extract_token(data)
    assert token, f"Staging login failed: {data}"
    return token


@pytest.fixture(scope="module")
async def deactivated_user_token() -> str:
    """
    Creates a fresh approved user, logs in, deactivates the account,
    then returns the token. Used to verify that a deactivated account
    is rejected when accessing protected endpoints.
    """
    user = create_approved_user_sync()
    async with HonoAPIClient() as client:
        login_resp = await client.post(APIEndpoints.LOGIN, json={
            "email":    user["email"],
            "password": user["password"],
        })
    skip_on_email_quota(login_resp)
    data = login_resp.json()
    token = _extract_token(data)
    assert token, f"Deactivate-user login failed: {data}"

    async with HonoAPIClient() as client:
        client.set_auth_token(token)
        await client.post(
            APIEndpoints.ME_DEACTIVATE,
            json={"password": user["password"]},
        )

    return token
