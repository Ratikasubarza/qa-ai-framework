import httpx
import pytest

from platforms.api.httpx_client import HonoAPIClient


@pytest.mark.asyncio
async def test_hono_api_client_injects_api_key_token_and_request_headers():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = request.headers
        return httpx.Response(200, json={"ok": True})

    async with HonoAPIClient(
        base_url="https://api.test",
        api_key="test-api-key",
        transport=httpx.MockTransport(handler),
    ) as client:
        client.set_auth_token("secret-token")
        response = await client.get(
            "/v1/users/me",
            headers={"x-trace-id": "trace-1"},
            expected_status=200,
        )

    assert response.json() == {"ok": True}
    assert captured["headers"]["x-api-key"] == "test-api-key"
    assert captured["headers"]["authorization"] == "Bearer secret-token"
    assert captured["headers"]["x-trace-id"] == "trace-1"


@pytest.mark.asyncio
async def test_hono_api_client_supports_no_api_key_mode():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = request.headers
        return httpx.Response(401, json={"message": "missing api key"})

    async with HonoAPIClient.no_api_key(
        base_url="https://api.test",
        transport=httpx.MockTransport(handler),
    ) as client:
        await client.get("/v1/users/me", expected_status=401)

    assert "x-api-key" not in captured["headers"]


@pytest.mark.asyncio
async def test_hono_api_client_expected_status_error_does_not_leak_body():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            500,
            json={
                "token": "secret-token",
                "email": "qa.user@example.com",
            },
        )

    async with HonoAPIClient(
        base_url="https://api.test",
        api_key="test-api-key",
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(AssertionError) as exc:
            await client.post("/v1/users/register", json={}, expected_status=200)

    message = str(exc.value)
    assert "secret-token" not in message
    assert "qa.user@example.com" not in message
    assert "POST /v1/users/register" in message


@pytest.mark.asyncio
async def test_hono_api_client_login_stores_auth_token():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/users/login":
            return httpx.Response(200, json={"data": {"accessToken": "login-token"}})
        captured["headers"] = request.headers
        return httpx.Response(200, json={"ok": True})

    async with HonoAPIClient(
        base_url="https://api.test",
        api_key="test-api-key",
        transport=httpx.MockTransport(handler),
    ) as client:
        token = await client.login("user@example.com", "password")
        await client.get("/v1/users/me")

    assert token == "login-token"
    assert captured["headers"]["authorization"] == "Bearer login-token"
