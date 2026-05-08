import pytest
import pytest_asyncio
import os
from dotenv import load_dotenv
from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator

load_dotenv(dotenv_path=".env")
EMAIL    = os.getenv("STAGING_EMAIL", "testingHonoA@mailinator.com")
PASSWORD = os.getenv("STAGING_PASSWORD", "P@ssTika1234#26")


@pytest_asyncio.fixture(scope="function")
async def auth_client():
    async with HonoAPIClient() as client:
        await client.login(EMAIL, PASSWORD)
        yield client


@pytest_asyncio.fixture(scope="function")
async def unauth_client():
    async with HonoAPIClient() as client:
        yield client


@pytest.mark.asyncio
async def test_TC_API_001_login_valid_credentials():
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/login", json={"email": EMAIL, "password": PASSWORD})
        SchemaValidator(response).status_ok().has_key("data").response_time_under(3000)
        data = response.json().get("data") or {}
        token = data.get("accessToken") or data.get("token")
        assert token, "Token not found"


@pytest.mark.asyncio
async def test_TC_API_002_login_wrong_password():
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/login", json={"email": EMAIL, "password": "WrongPass123!"})
        SchemaValidator(response).status_unauthorized()


@pytest.mark.asyncio
async def test_TC_API_003_login_invalid_email():
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/login", json={"email": "bad-email", "password": PASSWORD})
        assert response.status_code in [400, 401, 422]


@pytest.mark.asyncio
async def test_TC_API_004_login_missing_password():
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/login", json={"email": EMAIL})
        assert response.status_code in [400, 401, 422]


@pytest.mark.asyncio
async def test_TC_API_005_login_empty_body():
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/login", json={})
        assert response.status_code in [400, 401, 422]


@pytest.mark.asyncio
async def test_TC_API_006_search_authenticated(auth_client):
    response = await auth_client.get("/v1/search/posts", params={"q": "test"})
    print("Search: " + str(response.status_code) + " " + response.text[:100])
    assert response.status_code in [200, 400]
    SchemaValidator(response).response_time_under(5000)


@pytest.mark.asyncio
async def test_TC_API_007_search_unauthenticated(unauth_client):
    response = await unauth_client.get("/v1/search/posts", params={"q": "test"})
    assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_TC_API_008_search_empty_query(auth_client):
    response = await auth_client.get("/v1/search/posts", params={"q": ""})
    print("Empty: " + str(response.status_code))
    assert response.status_code in [200, 400, 422]


@pytest.mark.asyncio
async def test_TC_API_009_search_response_time(auth_client):
    response = await auth_client.get("/v1/search/posts", params={"q": "hono"})
    SchemaValidator(response).response_time_under(3000)
