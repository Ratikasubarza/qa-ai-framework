"""Moderation API Tests — POST /v1/posts/:post_id/not-interested"""
import pytest
import allure

from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator
from config.test_config import APIEndpoints

pytestmark = allure.feature("Moderation")

NONEXISTENT_POST_ID = "00000000-0000-0000-0000-000000000000"


@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_MOD_001_not_interested_valid_post(mod_token, mod_post_id):
    """TC-MOD-001 | Smoke | Mark post as not-interested returns 200"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.post_not_interested(mod_post_id),
            headers={"Authorization": f"Bearer {mod_token}"},
        )
    SchemaValidator(response).status_in(200, 201)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_MOD_002_not_interested_no_token(mod_post_id):
    """TC-MOD-002 | Security | Mark not-interested without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.post_not_interested(mod_post_id),
        )
    SchemaValidator(response).status_is(401)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_MOD_003_not_interested_nonexistent_post(mod_token):
    """TC-MOD-003 | Negative | Mark nonexistent post as not-interested returns 404"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.post_not_interested(NONEXISTENT_POST_ID),
            headers={"Authorization": f"Bearer {mod_token}"},
        )
    SchemaValidator(response).status_in(404, 400)
