"""Network API Tests — followers, following, suggestions"""
import pytest
import allure

from platforms.api.httpx_client import HonoAPIClient
from skills.assertions.api_assertions import APIAssertions
from config.test_config import APIEndpoints

pytestmark = allure.feature("Network")


# ── GET /v1/network/followers ─────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_NET_001_get_followers_authenticated(network_token):
    """TC-NET-001 | Smoke | Get followers returns 200 with data array"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.NETWORK_FOLLOWERS,
            headers={"Authorization": f"Bearer {network_token}"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body.get("code") == "OK"
    assert isinstance(body.get("data"), list)


@pytest.mark.api
async def test_TC_NET_002_get_followers_with_pagination(network_token):
    """TC-NET-002 | Functional | Get followers with page/limit params"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.NETWORK_FOLLOWERS,
            params={"page": 1, "limit": 10},
            headers={"Authorization": f"Bearer {network_token}"},
        )
    APIAssertions(response).status(200)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_NET_003_get_followers_no_token():
    """TC-NET-003 | Security | Get followers without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.get(APIEndpoints.NETWORK_FOLLOWERS)
    APIAssertions(response).status(401)


# ── GET /v1/network/following ─────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_NET_004_get_following_authenticated(network_token):
    """TC-NET-004 | Smoke | Get following returns 200 with data array"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.NETWORK_FOLLOWING,
            headers={"Authorization": f"Bearer {network_token}"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body.get("code") == "OK"
    assert isinstance(body.get("data"), list)


@pytest.mark.api
async def test_TC_NET_005_get_following_with_query(network_token):
    """TC-NET-005 | Functional | Get following with search query"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.NETWORK_FOLLOWING,
            params={"page": 1, "limit": 10, "query": "test"},
            headers={"Authorization": f"Bearer {network_token}"},
        )
    APIAssertions(response).status(200)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_NET_006_get_following_no_token():
    """TC-NET-006 | Security | Get following without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.get(APIEndpoints.NETWORK_FOLLOWING)
    APIAssertions(response).status(401)


# ── GET /v1/network/suggestions ───────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_NET_007_get_suggestions_authenticated(network_token):
    """TC-NET-007 | Smoke | Get network suggestions returns 200"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.NETWORK_SUGGESTIONS,
            params={"page": 1, "limit": 10},
            headers={"Authorization": f"Bearer {network_token}"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body.get("code") == "OK"


@pytest.mark.api
async def test_TC_NET_008_get_suggestions_schema(network_token):
    """TC-NET-008 | Functional | Suggestions data items have expected shape"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.NETWORK_SUGGESTIONS,
            params={"page": 1, "limit": 5},
            headers={"Authorization": f"Bearer {network_token}"},
        )
    assert response.status_code == 200
    body = response.json()
    data = body.get("data", [])
    if data:
        item = data[0]
        assert "id" in item or "creator" in item, f"Unexpected item shape: {item}"


@pytest.mark.negative
@pytest.mark.api
async def test_TC_NET_009_get_suggestions_no_token():
    """TC-NET-009 | Security | Get suggestions without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.get(APIEndpoints.NETWORK_SUGGESTIONS)
    APIAssertions(response).status(401)
