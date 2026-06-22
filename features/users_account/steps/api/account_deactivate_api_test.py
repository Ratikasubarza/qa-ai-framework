"""Account Deactivate API Tests — POST /v1/users/me/deactivate"""
import time
import random
import pytest
import allure
import pytest_asyncio

from core.db.test_user_helper import create_approved_user_sync
from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator
from skills.testing.helpers import skip_on_email_quota
from config.test_config import APIEndpoints

pytestmark = allure.feature("Account")

ENDPOINT = APIEndpoints.ME_DEACTIVATE


@pytest.fixture(scope="module")
def deactivate_user():
    suffix = f"{int(time.time())}{random.randint(100, 999)}"
    return create_approved_user_sync(suffix=suffix)


@pytest_asyncio.fixture(scope="module")
async def deactivate_token(deactivate_user) -> str:
    async with HonoAPIClient() as client:
        resp = await client.post(APIEndpoints.LOGIN, json={
            "email":    deactivate_user["email"],
            "password": deactivate_user["password"],
        })
    skip_on_email_quota(resp)
    data = resp.json()
    body = data.get("data", data)
    token = body.get("accessToken") or body.get("token", "")
    assert token, f"Login failed: {data}"
    return token


# ── Success ───────────────────────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ACC_010_deactivate_valid_password(deactivate_user, deactivate_token):
    """TC-ACC-010 | Smoke | Deactivate with correct password returns 200"""
    async with HonoAPIClient() as client:
        response = await client.post(
            ENDPOINT,
            json={"password": deactivate_user["password"]},
            headers={"Authorization": f"Bearer {deactivate_token}"},
        )
    SchemaValidator(response).status_in(200, 204)


# ── Unauthorized ──────────────────────────────────────────────────────────────

@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ACC_011_deactivate_no_token(deactivate_user):
    """TC-ACC-011 | Security | Deactivate without auth token returns 401"""
    async with HonoAPIClient() as client:
        response = await client.post(
            ENDPOINT,
            json={"password": deactivate_user["password"]},
        )
    SchemaValidator(response).status_is(401)


# ── Invalid input ─────────────────────────────────────────────────────────────

@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ACC_012_deactivate_wrong_password(deactivate_token):
    """TC-ACC-012 | Negative | Deactivate with wrong password returns 400/401"""
    async with HonoAPIClient() as client:
        response = await client.post(
            ENDPOINT,
            json={"password": "WrongPassword999!"},
            headers={"Authorization": f"Bearer {deactivate_token}"},
        )
    SchemaValidator(response).status_in(400, 401, 422)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ACC_013_deactivate_missing_password(deactivate_token):
    """TC-ACC-013 | Negative | Deactivate with missing password field returns 400/422"""
    async with HonoAPIClient() as client:
        response = await client.post(
            ENDPOINT,
            json={},
            headers={"Authorization": f"Bearer {deactivate_token}"},
        )
    SchemaValidator(response).status_in(400, 422)
