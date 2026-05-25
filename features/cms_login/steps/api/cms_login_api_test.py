"""CMS Login API Tests — POST /v1/users/login with resource: admin"""
import allure
import pytest

from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator
from features.cms_login.test_data.cms_login_test_data import CmsLoginTestData
from config.test_config import APIEndpoints

pytestmark = [allure.feature("CMS Login"), allure.suite("API")]


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_TC_CMS_API_001_login_valid_credentials():
    """TC-CMS-API-001 | Smoke | CMS login with valid credentials returns token"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.LOGIN,
            json=CmsLoginTestData.valid_payload(),
        )
    (SchemaValidator(response)
     .status_ok()
     .has_token())


@pytest.mark.negative
@pytest.mark.asyncio
async def test_TC_CMS_API_002_login_wrong_password():
    """TC-CMS-API-002 | Negative | CMS login with wrong password returns 401"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.LOGIN,
            json=CmsLoginTestData.wrong_password_payload(),
        )
    SchemaValidator(response).status_in(400, 401)


@pytest.mark.boundary
@pytest.mark.asyncio
async def test_TC_CMS_API_003_login_missing_resource():
    """TC-CMS-API-003 | Boundary | CMS login without resource field returns 4xx"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.LOGIN,
            json=CmsLoginTestData.missing_resource_payload(),
        )
    SchemaValidator(response).status_in(400, 401, 422)


@pytest.mark.negative
@pytest.mark.asyncio
async def test_TC_CMS_API_004_login_wrong_resource():
    """TC-CMS-API-004 | Negative | CMS login with wrong resource value returns 4xx"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.LOGIN,
            json=CmsLoginTestData.wrong_resource_payload(),
        )
    SchemaValidator(response).status_in(400, 401, 422)


@pytest.mark.performance
@pytest.mark.asyncio
async def test_TC_CMS_API_005_login_response_time():
    """TC-CMS-API-005 | Performance | CMS login response under 3s"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.LOGIN,
            json=CmsLoginTestData.valid_payload(),
        )
    SchemaValidator(response).response_time_under(CmsLoginTestData.MAX_RESPONSE_MS)


@pytest.mark.security
@pytest.mark.asyncio
async def test_TC_CMS_API_006_login_without_api_key():
    """TC-CMS-API-006 | Security | CMS login without x-api-key header returns 401"""
    async with HonoAPIClient.no_api_key() as client:
        response = await client.post(
            APIEndpoints.LOGIN,
            json=CmsLoginTestData.valid_payload(),
        )
    SchemaValidator(response).status_in(401, 403)


@pytest.mark.negative
@pytest.mark.asyncio
async def test_TC_CMS_API_007_login_invalid_email_format():
    """TC-CMS-API-007 | Negative | CMS login with invalid email format returns 400"""
    async with HonoAPIClient() as client:
        response = await client.post(APIEndpoints.LOGIN, json={
            "email":    CmsLoginTestData.INVALID_EMAIL,
            "password": CmsLoginTestData.VALID_PASSWORD,
            "resource": CmsLoginTestData.RESOURCE,
        })
    SchemaValidator(response).status_in(400, 422)


@pytest.mark.negative
@pytest.mark.asyncio
async def test_TC_CMS_API_008_login_empty_email():
    """TC-CMS-API-008 | Negative | CMS login with empty email returns 400"""
    async with HonoAPIClient() as client:
        response = await client.post(APIEndpoints.LOGIN, json={
            "email":    CmsLoginTestData.EMPTY_STRING,
            "password": CmsLoginTestData.VALID_PASSWORD,
            "resource": CmsLoginTestData.RESOURCE,
        })
    SchemaValidator(response).status_in(400, 422)


@pytest.mark.negative
@pytest.mark.asyncio
async def test_TC_CMS_API_009_login_empty_password():
    """TC-CMS-API-009 | Negative | CMS login with empty password returns 4xx"""
    async with HonoAPIClient() as client:
        response = await client.post(APIEndpoints.LOGIN, json={
            "email":    CmsLoginTestData.VALID_EMAIL,
            "password": CmsLoginTestData.EMPTY_STRING,
            "resource": CmsLoginTestData.RESOURCE,
        })
    SchemaValidator(response).status_in(400, 401, 422)


@pytest.mark.boundary
@pytest.mark.asyncio
async def test_TC_CMS_API_010_login_multiple_failed_attempts():
    """TC-CMS-API-010 | Boundary | Three consecutive wrong-password CMS logins all blocked"""
    async with HonoAPIClient() as client:
        for attempt in range(3):
            response = await client.post(
                APIEndpoints.LOGIN,
                json=CmsLoginTestData.wrong_password_payload(),
            )
            assert response.status_code in [400, 401], (
                f"Attempt {attempt + 1}: expected 4xx, got {response.status_code}"
            )
