"""Create Post API Tests — POST /v1/posts"""
import pytest
import allure

from platforms.api.httpx_client import HonoAPIClient
from skills.assertions.api_assertions import APIAssertions
from skills.testing.helpers import skip_on_email_quota
from features.posts.test_data.create_post_test_data import (
    CreatePostPayload, CreatePostTestData,
)

pytestmark = allure.feature("Posts")

ENDPOINT = "/v1/posts"


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _create_post(payload: dict, token: str) -> object:
    async with HonoAPIClient() as client:
        return await client.post(
            ENDPOINT,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )


# ── Smoke ─────────────────────────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.asyncio
async def test_TC_POST_API_001_create_post_valid_data(post_token):
    """TC-POST-API-001 | Smoke | Create post with valid minimal data"""
    payload = CreatePostPayload.valid().as_dict()
    response = await _create_post(payload, post_token)

    (APIAssertions(response)
     .status_in(200, 201)
     .code_equals(CreatePostTestData.SUCCESS_CODE)
     .has_key("id")
     .attach_to_report("create_post_response"))


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_TC_POST_API_002_create_post_with_media(post_token):
    """TC-POST-API-002 | Smoke | Create post with S3 media URL"""
    payload = CreatePostPayload.with_media().as_dict()
    response = await _create_post(payload, post_token)

    (APIAssertions(response)
     .status_in(200, 201)
     .code_equals(CreatePostTestData.SUCCESS_CODE)
     .has_key("id"))


# ── Functional ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_TC_POST_API_003_create_anonymous_post(post_token):
    """TC-POST-API-003 | Functional | Create anonymous post sets is_anonymous true"""
    payload = CreatePostPayload.anonymous().as_dict()
    response = await _create_post(payload, post_token)

    assert response.status_code in (200, 201), (
        f"Expected 200/201, got {response.status_code}: {response.text[:200]}"
    )
    data = response.json().get("data", response.json())
    assert data.get("is_anonymous") is True, (
        f"is_anonymous should be True in response, got: {data.get('is_anonymous')}"
    )


@pytest.mark.asyncio
async def test_TC_POST_API_004_create_post_multiple_topics(post_token):
    """TC-POST-API-004 | Functional | Create post with 3 topic_ids returns topics array"""
    payload = CreatePostPayload.multiple_topics().as_dict()
    response = await _create_post(payload, post_token)

    assert response.status_code in (200, 201), (
        f"Expected 200/201, got {response.status_code}: {response.text[:200]}"
    )
    data = response.json().get("data", response.json())
    topics = data.get("topics", [])
    assert len(topics) > 0, f"Expected topics in response, got: {topics}"


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_TC_POST_API_005_create_post_schema_validation(post_token):
    """TC-POST-API-005 | Smoke | Response schema contains all required fields"""
    payload = CreatePostPayload.valid().as_dict()
    response = await _create_post(payload, post_token)

    assert response.status_code in (200, 201)
    data = response.json().get("data", response.json())

    missing = CreatePostTestData.REQUIRED_RESPONSE_KEYS - set(data.keys())
    assert not missing, f"Missing required keys in response: {sorted(missing)}"

    engagement = data.get("engagement", {})
    missing_eng = CreatePostTestData.REQUIRED_ENGAGEMENT_KEYS - set(engagement.keys())
    assert not missing_eng, f"Missing engagement keys: {sorted(missing_eng)}"

    assert engagement.get("like_count") == 0,    "New post like_count should be 0"
    assert engagement.get("comment_count") == 0, "New post comment_count should be 0"
    assert engagement.get("repost_count") == 0,  "New post repost_count should be 0"


@pytest.mark.asyncio
async def test_TC_POST_API_006_create_post_visibility_everyone(post_token):
    """TC-POST-API-006 | Functional | Create post with visibility=EVERYONE is accepted"""
    payload = CreatePostPayload.with_visibility("EVERYONE").as_dict()
    response = await _create_post(payload, post_token)

    assert response.status_code in (200, 201), (
        f"Expected 200/201, got {response.status_code}: {response.text[:200]}"
    )


# ── Security ──────────────────────────────────────────────────────────────────

@pytest.mark.security
@pytest.mark.asyncio
async def test_TC_POST_API_007_create_post_no_token():
    """TC-POST-API-007 | Security | Create post without auth token returns 401"""
    async with HonoAPIClient() as client:
        response = await client.post(ENDPOINT, json=CreatePostPayload.valid().as_dict())

    APIAssertions(response).status(401)


@pytest.mark.security
@pytest.mark.asyncio
async def test_TC_POST_API_008_create_post_no_api_key():
    """TC-POST-API-008 | Security | Create post without x-api-key header returns 401"""
    import httpx
    import os
    async with httpx.AsyncClient(
        base_url=os.getenv("HONO_API_URL", "https://api-dev.thehono.com"),
        timeout=30,
    ) as client:
        response = await client.post(
            ENDPOINT,
            json=CreatePostPayload.valid().as_dict(),
            headers={
                "Authorization": "Bearer fake_token_no_api_key",
                "Content-Type": "application/json",
            },
        )

    APIAssertions(response).status(401)


# ── Negative ──────────────────────────────────────────────────────────────────

@pytest.mark.negative
@pytest.mark.asyncio
async def test_TC_POST_API_009_create_post_no_topics(post_token):
    """TC-POST-API-009 | Negative | Create post with empty topic_ids returns 422"""
    payload = CreatePostPayload.no_topics().as_dict()
    response = await _create_post(payload, post_token)

    (APIAssertions(response)
     .status(422)
     .code_equals(CreatePostTestData.VALIDATION_CODE)
     .body_contains_error("topic"))


@pytest.mark.negative
@pytest.mark.asyncio
async def test_TC_POST_API_010_create_post_empty_content(post_token):
    """TC-POST-API-010 | Negative | Create post with empty content returns 400 or 422"""
    payload = CreatePostPayload.empty_content().as_dict()
    response = await _create_post(payload, post_token)

    APIAssertions(response).status_in(400, 422)


@pytest.mark.negative
@pytest.mark.asyncio
async def test_TC_POST_API_011_create_post_missing_content(post_token):
    """TC-POST-API-011 | Negative | Create post without content field returns 400 or 422"""
    payload = CreatePostPayload.valid().without("content")
    response = await _create_post(payload, post_token)

    APIAssertions(response).status_in(400, 422)


@pytest.mark.negative
@pytest.mark.asyncio
async def test_TC_POST_API_012_create_post_invalid_visibility(post_token):
    """TC-POST-API-012 | Negative | Create post with invalid visibility value returns 400 or 422"""
    payload = CreatePostPayload.with_visibility(CreatePostTestData.VISIBILITY_INVALID).as_dict()
    response = await _create_post(payload, post_token)

    APIAssertions(response).status_in(400, 422)


@pytest.mark.negative
@pytest.mark.asyncio
async def test_TC_POST_API_013_create_post_missing_topic_ids(post_token):
    """TC-POST-API-013 | Negative | Create post without topic_ids field returns 400 or 422"""
    payload = CreatePostPayload.valid().without("topic_ids")
    response = await _create_post(payload, post_token)

    APIAssertions(response).status_in(400, 422)


# ── Boundary ──────────────────────────────────────────────────────────────────

@pytest.mark.boundary
@pytest.mark.asyncio
async def test_TC_POST_API_014_create_post_long_content(post_token):
    """TC-POST-API-014 | Boundary | Create post with 5000-char content — documents limit"""
    payload = CreatePostPayload.long_content(5000).as_dict()
    response = await _create_post(payload, post_token)

    APIAssertions(response).status_in(200, 201, 400, 422)
    print(f"\n  5000-char content → {response.status_code}")


@pytest.mark.boundary
@pytest.mark.asyncio
async def test_TC_POST_API_015_create_post_empty_body(post_token):
    """TC-POST-API-015 | Boundary | Create post with completely empty body returns 400 or 422"""
    response = await _create_post({}, post_token)

    APIAssertions(response).status_in(400, 422)


# ── Performance ───────────────────────────────────────────────────────────────

@pytest.mark.performance
@pytest.mark.asyncio
async def test_TC_POST_API_016_create_post_response_time(post_token):
    """TC-POST-API-016 | Performance | Create post response time under 3000ms"""
    payload = CreatePostPayload.valid().as_dict()
    response = await _create_post(payload, post_token)

    assert response.status_code in (200, 201)
    APIAssertions(response).response_time_under(CreatePostTestData.MAX_RESPONSE_MS)
