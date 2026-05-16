"""CMS Login API Tests — POST /v1/users/login with resource: admin"""
import allure
import pytest

from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator
from features.cms_login.test_data.cms_login_test_data import CmsLoginTestData
from config.test_config import TestConfig, APIEndpoints

pytestmark = allure.feature("CMS Login")


@pytest.mark.asyncio
async def test_TC_CMS_API_001_login_valid_credentials():
    """
    TC-CMS-API-001 | Smoke | CMS login with valid credentials returns token
    Given: API available
    When: POST /v1/users/login with email + password + resource=admin
    Then: 200 + accessToken returned
    """
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.LOGIN,
            json=CmsLoginTestData.valid_payload()
        )
    SchemaValidator(response).status_ok()
    data = response.json()
    body = data.get("data", data)
    assert "accessToken" in body or "token" in body, \
        f"Token not found in response: {data}"
    print(f"\n✓ CMS Login success — token received")


@pytest.mark.asyncio
async def test_TC_CMS_API_002_login_wrong_password():
    """
    TC-CMS-API-002 | Negative | CMS login with wrong password returns 401
    """
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.LOGIN,
            json=CmsLoginTestData.wrong_password_payload()
        )
    assert response.status_code in [401, 400], \
        f"Expected 401, got: {response.status_code}"
    print(f"\n✓ Wrong password blocked: {response.status_code}")


@pytest.mark.asyncio
async def test_TC_CMS_API_003_login_missing_resource():
    """
    TC-CMS-API-003 | Boundary | CMS login without resource field
    Given: resource field is missing
    Then: 400 or 401 returned
    """
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.LOGIN,
            json=CmsLoginTestData.missing_resource_payload()
        )
    assert response.status_code in [400, 401, 422], \
        f"Expected 4xx, got: {response.status_code}"
    print(f"\n✓ Missing resource blocked: {response.status_code}")


@pytest.mark.asyncio
async def test_TC_CMS_API_004_login_wrong_resource():
    """
    TC-CMS-API-004 | Negative | CMS login with wrong resource value
    Given: resource is not "admin"
    Then: 400 or 401 returned
    """
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.LOGIN,
            json=CmsLoginTestData.wrong_resource_payload()
        )
    assert response.status_code in [400, 401, 422], \
        f"Expected 4xx, got: {response.status_code}"
    print(f"\n✓ Wrong resource blocked: {response.status_code}")


@pytest.mark.asyncio
async def test_TC_CMS_API_005_login_response_time():
    """
    TC-CMS-API-005 | Performance | CMS login response under 3s
    """
    import time
    async with HonoAPIClient() as client:
        start = time.time()
        response = await client.post(
            APIEndpoints.LOGIN,
            json=CmsLoginTestData.valid_payload()
        )
        elapsed_ms = (time.time() - start) * 1000

    assert elapsed_ms < CmsLoginTestData.MAX_RESPONSE_MS, \
        f"Response too slow: {elapsed_ms:.0f}ms"
    print(f"\n✓ Response time: {elapsed_ms:.0f}ms")


# ── Extended CMS Login Tests ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_TC_CMS_API_006_login_without_api_key():
    """TC-CMS-API-006 | Security | CMS login without x-api-key header returns 401"""
    import httpx, os
    async with httpx.AsyncClient(
        base_url=os.getenv("HONO_API_URL"),
        timeout=30,
    ) as client:
        response = await client.post(
            APIEndpoints.LOGIN,
            json=CmsLoginTestData.valid_payload(),
        )
    assert response.status_code in [401, 403], \
        f"Expected 401/403 without API key, got: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_CMS_API_007_login_invalid_email_format():
    """TC-CMS-API-007 | Negative | CMS login with invalid email format returns 400"""
    async with HonoAPIClient() as client:
        response = await client.post(APIEndpoints.LOGIN, json={
            "email":    CmsLoginTestData.INVALID_EMAIL,
            "password": CmsLoginTestData.VALID_PASSWORD,
            "resource": CmsLoginTestData.RESOURCE,
        })
    assert response.status_code in [400, 422], \
        f"Expected 400/422 for invalid email format, got: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_CMS_API_008_login_empty_email():
    """TC-CMS-API-008 | Negative | CMS login with empty email returns 400"""
    async with HonoAPIClient() as client:
        response = await client.post(APIEndpoints.LOGIN, json={
            "email":    CmsLoginTestData.EMPTY_STRING,
            "password": CmsLoginTestData.VALID_PASSWORD,
            "resource": CmsLoginTestData.RESOURCE,
        })
    assert response.status_code in [400, 422], \
        f"Expected 400/422 for empty email, got: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_CMS_API_009_login_empty_password():
    """TC-CMS-API-009 | Negative | CMS login with empty password returns 4xx"""
    async with HonoAPIClient() as client:
        response = await client.post(APIEndpoints.LOGIN, json={
            "email":    CmsLoginTestData.VALID_EMAIL,
            "password": CmsLoginTestData.EMPTY_STRING,
            "resource": CmsLoginTestData.RESOURCE,
        })
    assert response.status_code in [400, 401, 422], \
        f"Expected 4xx for empty password, got: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_CMS_API_010_login_multiple_failed_attempts():
    """TC-CMS-API-010 | Boundary | Three consecutive wrong-password CMS logins all blocked"""
    async with HonoAPIClient() as client:
        for attempt in range(3):
            response = await client.post(
                APIEndpoints.LOGIN,
                json=CmsLoginTestData.wrong_password_payload(),
            )
            assert response.status_code in [400, 401], \
                f"Attempt {attempt + 1}: expected 4xx, got {response.status_code}"
    print("\n✓ 3 failed CMS login attempts all blocked")
