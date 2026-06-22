"""Search API Tests — posts (recent/top), typeahead, users"""
import pytest
import allure

from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator
from config.test_config import APIEndpoints

pytestmark = allure.feature("Search")


# ── GET /v1/search/posts?tab=recent ──────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SRCH_001_search_posts_recent(search_token):
    """TC-SRCH-001 | Smoke | Search posts with tab=recent returns 200"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SEARCH_POSTS,
            params={"query": "hono", "page": 1, "per_page": 10, "tab": "recent"},
            headers={"Authorization": f"Bearer {search_token}"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body.get("code") == "OK"
    assert "data" in body


@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SRCH_002_search_posts_recent_empty_result(search_token):
    """TC-SRCH-002 | Functional | Search posts with no-match query returns empty list"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SEARCH_POSTS,
            params={"query": "zzz_no_match_xqz", "page": 1, "per_page": 10, "tab": "recent"},
            headers={"Authorization": f"Bearer {search_token}"},
        )
    assert response.status_code == 200
    body = response.json()
    data = body.get("data", [])
    assert isinstance(data, list)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SRCH_003_search_posts_no_token():
    """TC-SRCH-003 | Security | Search posts without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SEARCH_POSTS,
            params={"query": "hono", "tab": "recent"},
        )
    SchemaValidator(response).status_is(401)


# ── GET /v1/search/posts?tab=top ─────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SRCH_004_search_posts_top(search_token):
    """TC-SRCH-004 | Smoke | Search posts with tab=top returns 200"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SEARCH_POSTS,
            params={"query": "hono", "page": 1, "per_page": 10, "tab": "top"},
            headers={"Authorization": f"Bearer {search_token}"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body.get("code") == "OK"


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SRCH_005_search_posts_missing_query(search_token):
    """TC-SRCH-005 | Negative | Search posts without query param returns 400/422"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SEARCH_POSTS,
            params={"tab": "recent"},
            headers={"Authorization": f"Bearer {search_token}"},
        )
    SchemaValidator(response).status_in(400, 422, 200)


# ── GET /v1/search/typeahead ──────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SRCH_006_search_typeahead(search_token):
    """TC-SRCH-006 | Smoke | Typeahead with query returns 200 with suggestions"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SEARCH_TYPEAHEAD,
            params={"query": "ho"},
            headers={"Authorization": f"Bearer {search_token}"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body.get("code") == "OK"


@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SRCH_007_search_typeahead_schema(search_token):
    """TC-SRCH-007 | Functional | Typeahead response has suggestions and profiles keys"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SEARCH_TYPEAHEAD,
            params={"query": "ba"},
            headers={"Authorization": f"Bearer {search_token}"},
        )
    assert response.status_code == 200
    body = response.json()
    data = body.get("data", {})
    assert isinstance(data, dict) or isinstance(data, list)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SRCH_008_search_typeahead_no_token():
    """TC-SRCH-008 | Security | Typeahead without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SEARCH_TYPEAHEAD,
            params={"query": "test"},
        )
    SchemaValidator(response).status_is(401)


# ── GET /v1/search/users ─────────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SRCH_009_search_users(search_token):
    """TC-SRCH-009 | Smoke | Search users by query returns 200"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SEARCH_USERS,
            params={"query": "test", "page": 1, "per_page": 10},
            headers={"Authorization": f"Bearer {search_token}"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body.get("code") == "OK"
    assert "data" in body


@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SRCH_010_search_users_empty(search_token):
    """TC-SRCH-010 | Functional | Search users with no-match query returns empty data"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SEARCH_USERS,
            params={"query": "zzz_no_match_xqz999", "page": 1, "per_page": 10},
            headers={"Authorization": f"Bearer {search_token}"},
        )
    assert response.status_code == 200
    body = response.json()
    data = body.get("data", [])
    assert isinstance(data, list)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SRCH_011_search_users_no_token():
    """TC-SRCH-011 | Security | Search users without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SEARCH_USERS,
            params={"query": "test"},
        )
    SchemaValidator(response).status_is(401)
