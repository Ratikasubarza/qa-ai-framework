"""
CMS Login API Tests — POST /v1/users/login dengan resource: admin
Target: api-dev.thehono.com
"""
import pytest
from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator
from features.cms_login.test_data.cms_login_test_data import CmsLoginTestData
from config.test_config import TestConfig


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
            "/v1/users/login",
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
            "/v1/users/login",
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
            "/v1/users/login",
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
            "/v1/users/login",
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
            "/v1/users/login",
            json=CmsLoginTestData.valid_payload()
        )
        elapsed_ms = (time.time() - start) * 1000

    assert elapsed_ms < CmsLoginTestData.MAX_RESPONSE_MS, \
        f"Response too slow: {elapsed_ms:.0f}ms"
    print(f"\n✓ Response time: {elapsed_ms:.0f}ms")
