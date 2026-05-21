import allure
import pytest
import pytest_asyncio
import os
from dotenv import load_dotenv
from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator
from config.test_config import APIEndpoints, Timeouts

load_dotenv(dotenv_path=".env")
EMAIL    = os.getenv("STAGING_EMAIL", "")
PASSWORD = os.getenv("STAGING_PASSWORD", "")

pytestmark = allure.feature("Login")


@pytest_asyncio.fixture(scope="function")
async def auth_client():
    async with HonoAPIClient() as client:
        await client.login(EMAIL, PASSWORD)
        yield client


@pytest_asyncio.fixture(scope="function")
async def unauth_client():
    async with HonoAPIClient() as client:
        yield client


@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_API_001_login_valid_credentials():
    """TC-API-001 | Smoke | Valid credentials return 200 + auth token"""
    async with HonoAPIClient() as client:
        response = await client.post(APIEndpoints.LOGIN, json={"email": EMAIL, "password": PASSWORD})
        SchemaValidator(response).status_ok().has_token().response_time_under(Timeouts.API_SLA_MS)
        body = response.json()
        data = body.get("data", body) if isinstance(body, dict) else {}
        token = data.get("accessToken") or data.get("token")
        assert token, "Token not found"


@pytest.mark.sanity
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_API_002_login_wrong_password():
    """TC-API-002 | Sanity | Wrong password returns 401"""
    async with HonoAPIClient() as client:
        response = await client.post(APIEndpoints.LOGIN, json={"email": EMAIL, "password": "WrongPass123!"})
        SchemaValidator(response).status_unauthorized()


@pytest.mark.sanity
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_API_003_login_invalid_email():
    """TC-API-003 | Sanity | Invalid email format returns 400/422"""
    async with HonoAPIClient() as client:
        response = await client.post(APIEndpoints.LOGIN, json={"email": "bad-email", "password": PASSWORD})
        assert response.status_code in [400, 401, 422]


@pytest.mark.sanity
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_API_004_login_missing_password():
    """TC-API-004 | Sanity | Missing password returns 400/422"""
    async with HonoAPIClient() as client:
        response = await client.post(APIEndpoints.LOGIN, json={"email": EMAIL})
        assert response.status_code in [400, 401, 422]


@pytest.mark.regression
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_API_005_login_empty_body():
    """TC-API-005 | Regression | Empty body returns 400/422"""
    async with HonoAPIClient() as client:
        response = await client.post(APIEndpoints.LOGIN, json={})
        assert response.status_code in [400, 401, 422]


@pytest.mark.regression
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_API_006_search_authenticated(auth_client):
    """TC-API-006 | Regression | Search with auth token returns 200/400"""
    response = await auth_client.get(APIEndpoints.SEARCH_POSTS, params={"q": "test"})
    print("Search: " + str(response.status_code) + " " + response.text[:100])
    assert response.status_code in [200, 400]
    SchemaValidator(response).response_time_under(5000)


@pytest.mark.sanity
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_API_007_search_unauthenticated(unauth_client):
    """TC-API-007 | Sanity | Search without auth returns 401/403"""
    response = await unauth_client.get(APIEndpoints.SEARCH_POSTS, params={"q": "test"})
    assert response.status_code in [401, 403]


@pytest.mark.regression
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_API_008_search_empty_query(auth_client):
    """TC-API-008 | Regression | Empty search query returns 200/400/422"""
    response = await auth_client.get(APIEndpoints.SEARCH_POSTS, params={"q": ""})
    print("Empty: " + str(response.status_code))
    assert response.status_code in [200, 400, 422]


@pytest.mark.performance
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_API_009_search_response_time(auth_client):
    """TC-API-009 | Performance | Search response under SLA"""
    response = await auth_client.get(APIEndpoints.SEARCH_POSTS, params={"q": "hono"})
    SchemaValidator(response).response_time_under(Timeouts.API_SLA_MS)


@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_API_010_get_profile_authenticated(auth_client):
    """TC-API-010 | Smoke | Get profile with valid token returns 200"""
    response = await auth_client.get(APIEndpoints.ME)
    validator = SchemaValidator(response)
    validator.status_ok()
    data = response.json()
    assert "data" in data or "email" in data or "id" in data, \
        f"Profile response missing expected fields: {data}"
    print(f"\n✓ Profile: {data.get('data', data)}")


@pytest.mark.security
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_API_011_get_profile_unauthenticated(unauth_client):
    """TC-API-011 | Security | Get profile without token returns 401"""
    response = await unauth_client.get(APIEndpoints.ME)
    assert response.status_code == 401, f'Expected 401, got: {response.status_code}'


@pytest.mark.security
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_API_012_login_without_api_key():
    """TC-API-012 | Security | Login without x-api-key header returns 401"""
    import httpx
    async with httpx.AsyncClient(
        base_url=os.getenv("HONO_API_URL"),
        timeout=Timeouts.API_REQUEST,
    ) as client:
        response = await client.post(
            APIEndpoints.LOGIN,
            json={"email": EMAIL, "password": PASSWORD},
        )
    assert response.status_code in [401, 403], \
        f"Expected 401/403 without API key, got: {response.status_code}"


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_API_013_login_empty_email():
    """TC-API-013 | Negative | Login with empty email string returns 400"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.LOGIN,
            json={"email": "", "password": PASSWORD},
        )
    assert response.status_code in [400, 422], \
        f"Expected 400/422 for empty email, got: {response.status_code}"


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_API_014_login_empty_password():
    """TC-API-014 | Negative | Login with empty password string returns 4xx"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.LOGIN,
            json={"email": EMAIL, "password": ""},
        )
    assert response.status_code in [400, 401, 422], \
        f"Expected 4xx for empty password, got: {response.status_code}"


@pytest.mark.performance
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_API_016_login_response_time():
    """TC-API-016 | Performance | Login response time under 3s"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.LOGIN,
            json={"email": EMAIL, "password": PASSWORD},
        )
    SchemaValidator(response).response_time_under(Timeouts.API_SLA_MS)


@pytest.mark.security
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_API_017_login_sql_injection_email():
    """TC-API-017 | Security | SQL injection in email is blocked"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.LOGIN,
            json={"email": "' OR 1=1 --", "password": PASSWORD},
        )
    assert response.status_code in [400, 401, 422], \
        f"Expected 4xx for SQL injection email, got: {response.status_code}"


@pytest.mark.boundary
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_API_018_login_very_long_email():
    """TC-API-018 | Boundary | 500-char email is handled gracefully"""
    long_email = "a" * 490 + "@test.com"
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.LOGIN,
            json={"email": long_email, "password": PASSWORD},
        )
    assert response.status_code in [400, 401, 422], \
        f"Expected 4xx for very long email, got: {response.status_code}"


@pytest.mark.boundary
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_API_019_login_email_case_sensitivity():
    """TC-API-019 | Boundary | Uppercase email — documents case sensitivity behavior"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.LOGIN,
            json={"email": EMAIL.upper(), "password": PASSWORD},
        )
    assert response.status_code in [200, 400, 401], \
        f"Unexpected status for uppercase email: {response.status_code}"
    print(f"\n  Case sensitivity: {EMAIL.upper()} → {response.status_code}")


@pytest.mark.security
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_API_020_login_multiple_failed_attempts():
    """TC-API-020 | Security | Three consecutive wrong-password attempts all return 401"""
    async with HonoAPIClient() as client:
        for attempt in range(3):
            response = await client.post(
                APIEndpoints.LOGIN,
                json={"email": EMAIL, "password": "WrongPass!"},
            )
            assert response.status_code == 401, \
                f"Attempt {attempt + 1}: expected 401, got {response.status_code}"
    print("\n✓ 3 failed login attempts all returned 401")
