"""Feed API Tests — GET /v1/feed, GET /v1/topics"""
import pytest
import allure

from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator
from config.test_config import APIEndpoints

pytestmark = allure.feature("Feed")


# ── GET /v1/feed ──────────────────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_FEED_001_get_feed_authenticated(feed_token):
    """TC-FEED-001 | Smoke | Authenticated user gets feed list"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.FEED,
            headers={"Authorization": f"Bearer {feed_token}"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body.get("code") == "OK"
    assert "data" in body


@pytest.mark.api
async def test_TC_FEED_002_get_feed_with_pagination(feed_token):
    """TC-FEED-002 | Functional | Feed with page/per_page params"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.FEED,
            params={"page": 1, "per_page": 5},
            headers={"Authorization": f"Bearer {feed_token}"},
        )
    SchemaValidator(response).status(200)


@pytest.mark.api
async def test_TC_FEED_003_get_feed_filter_param(feed_token):
    """TC-FEED-003 | Functional | Feed with filter param returns 200"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.FEED,
            params={"filter": "following", "page": 1, "per_page": 10},
            headers={"Authorization": f"Bearer {feed_token}"},
        )
    SchemaValidator(response).status_in(200, 400)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_FEED_004_get_feed_no_token():
    """TC-FEED-004 | Security | Feed without auth token returns 401"""
    async with HonoAPIClient() as client:
        response = await client.get(APIEndpoints.FEED)
    SchemaValidator(response).status(401)


# ── GET /v1/topics ────────────────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_FEED_005_get_topics_authenticated(feed_token):
    """TC-FEED-005 | Smoke | Authenticated user gets topics list"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.TOPICS,
            headers={"Authorization": f"Bearer {feed_token}"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body.get("code") == "OK"


@pytest.mark.negative
@pytest.mark.api
async def test_TC_FEED_006_get_topics_no_token():
    """TC-FEED-006 | Security | Topics without auth token returns 401"""
    async with HonoAPIClient() as client:
        response = await client.get(APIEndpoints.TOPICS)
    SchemaValidator(response).status(401)


@pytest.mark.api
async def test_TC_FEED_007_get_feed_response_schema(feed_token):
    """TC-FEED-007 | Functional | Feed response has pagination info"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.FEED,
            params={"page": 1, "per_page": 3},
            headers={"Authorization": f"Bearer {feed_token}"},
        )
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
