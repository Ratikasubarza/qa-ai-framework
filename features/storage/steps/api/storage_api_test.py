"""Storage API Tests — GET /v1/storage/presign/:key"""
import pytest
import allure

from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator
from config.test_config import APIEndpoints

pytestmark = allure.feature("Storage")

SAMPLE_KEY = "profiles/00000000-0000-0000-0000-000000000000/sample.jpg"
INVALID_KEY = "invalid/path"


@pytest.mark.smoke
@pytest.mark.api
async def test_TC_STR_001_presign_valid_key_format(storage_token):
    """TC-STR-001 | Smoke | Get presigned URL with valid key path returns 200 or 404"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.storage_presign(SAMPLE_KEY),
            headers={"Authorization": f"Bearer {storage_token}"},
        )
    SchemaValidator(response).status_in(200, 404)
    if response.status_code == 200:
        body = response.json()
        data = body.get("data", {})
        assert "url" in data


@pytest.mark.negative
@pytest.mark.api
async def test_TC_STR_002_presign_no_token():
    """TC-STR-002 | Security | Presign URL without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.storage_presign(SAMPLE_KEY),
        )
    SchemaValidator(response).status(401)


@pytest.mark.api
async def test_TC_STR_003_presign_response_schema(storage_token):
    """TC-STR-003 | Functional | Presign URL response has code field"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.storage_presign(SAMPLE_KEY),
            headers={"Authorization": f"Bearer {storage_token}"},
        )
    assert response.status_code in (200, 404)
    body = response.json()
    assert "code" in body
