"""Posts CRUD API Tests — GET/PUT/DELETE /v1/posts/:id, visibility, media, mentionable"""
import pytest
import allure

from platforms.api.httpx_client import HonoAPIClient
from skills.assertions.api_assertions import APIAssertions
from config.test_config import APIEndpoints

pytestmark = allure.feature("Posts")

NONEXISTENT_POST_ID = "00000000-0000-0000-0000-000000000000"


# ── GET /v1/posts/:post_id ────────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_POST_API_020_get_post_by_id(post_token, created_post_id):
    """TC-POST-API-020 | Smoke | Get post detail by valid post_id"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.post_detail(created_post_id),
            headers={"Authorization": f"Bearer {post_token}"},
        )
    assert response.status_code == 200
    body = response.json()
    data = body.get("data", body)
    assert data.get("id") == created_post_id


@pytest.mark.negative
@pytest.mark.api
async def test_TC_POST_API_021_get_post_not_found(post_token):
    """TC-POST-API-021 | Negative | Get post with nonexistent ID returns 404"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.post_detail(NONEXISTENT_POST_ID),
            headers={"Authorization": f"Bearer {post_token}"},
        )
    APIAssertions(response).status_in(404, 400)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_POST_API_022_get_post_no_token(created_post_id):
    """TC-POST-API-022 | Security | Get post without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.get(APIEndpoints.post_detail(created_post_id))
    APIAssertions(response).status(401)


# ── PUT /v1/posts/:post_id ────────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_POST_API_023_edit_post_valid(post_token, created_post_id):
    """TC-POST-API-023 | Smoke | Edit post content returns 200"""
    from features.posts.test_data.create_post_test_data import TOPIC_PODCASTING
    async with HonoAPIClient() as client:
        response = await client.put(
            APIEndpoints.post_detail(created_post_id),
            json={
                "content":   "Updated QA test post content",
                "topic_ids": [TOPIC_PODCASTING],
            },
            headers={"Authorization": f"Bearer {post_token}"},
        )
    APIAssertions(response).status_in(200, 201)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_POST_API_024_edit_post_no_token(created_post_id):
    """TC-POST-API-024 | Security | Edit post without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.put(
            APIEndpoints.post_detail(created_post_id),
            json={"content": "Unauthorized edit"},
        )
    APIAssertions(response).status(401)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_POST_API_025_edit_post_not_found(post_token):
    """TC-POST-API-025 | Negative | Edit nonexistent post returns 404"""
    from features.posts.test_data.create_post_test_data import TOPIC_PODCASTING
    async with HonoAPIClient() as client:
        response = await client.put(
            APIEndpoints.post_detail(NONEXISTENT_POST_ID),
            json={"content": "Ghost edit", "topic_ids": [TOPIC_PODCASTING]},
            headers={"Authorization": f"Bearer {post_token}"},
        )
    APIAssertions(response).status_in(403, 404)


# ── PUT /v1/posts/:post_id/visibility ─────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_POST_API_026_change_visibility_valid(post_token, created_post_id):
    """TC-POST-API-026 | Smoke | Change post visibility to EVERYONE"""
    async with HonoAPIClient() as client:
        response = await client.put(
            APIEndpoints.post_visibility(created_post_id),
            json={"visibility": "EVERYONE"},
            headers={"Authorization": f"Bearer {post_token}"},
        )
    APIAssertions(response).status_in(200, 201)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_POST_API_027_change_visibility_invalid_value(post_token, created_post_id):
    """TC-POST-API-027 | Negative | Invalid visibility value returns 400/422"""
    async with HonoAPIClient() as client:
        response = await client.put(
            APIEndpoints.post_visibility(created_post_id),
            json={"visibility": "PRIVATE_MODE"},
            headers={"Authorization": f"Bearer {post_token}"},
        )
    APIAssertions(response).status_in(400, 422)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_POST_API_028_change_visibility_no_token(created_post_id):
    """TC-POST-API-028 | Security | Change visibility without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.put(
            APIEndpoints.post_visibility(created_post_id),
            json={"visibility": "PUBLIC"},
        )
    APIAssertions(response).status(401)


# ── GET /v1/users/:user_id/posts ─────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_POST_API_029_get_user_posts(post_token, post_user):
    """TC-POST-API-029 | Smoke | Get own user posts returns 200"""
    user_id = post_user.get("id", "")
    if not user_id:
        pytest.skip("user_id not available in post_user fixture")
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.user_posts(user_id),
            params={"page": 1, "per_page": 10},
            headers={"Authorization": f"Bearer {post_token}"},
        )
    APIAssertions(response).status(200)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_POST_API_030_get_user_posts_no_token(post_user):
    """TC-POST-API-030 | Security | Get user posts without auth returns 401"""
    user_id = post_user.get("id", "nonexistent-id")
    async with HonoAPIClient() as client:
        response = await client.get(APIEndpoints.user_posts(user_id))
    APIAssertions(response).status(401)


# ── GET /v1/users/:id/media ───────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_POST_API_031_get_user_media(post_token, post_user):
    """TC-POST-API-031 | Smoke | Get user media returns 200"""
    user_id = post_user.get("id", "")
    if not user_id:
        pytest.skip("user_id not available in post_user fixture")
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.user_media(user_id),
            params={"page": 1, "per_page": 10},
            headers={"Authorization": f"Bearer {post_token}"},
        )
    APIAssertions(response).status(200)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_POST_API_032_get_user_media_no_token(post_user):
    """TC-POST-API-032 | Security | Get user media without auth returns 401"""
    user_id = post_user.get("id", "nonexistent-id")
    async with HonoAPIClient() as client:
        response = await client.get(APIEndpoints.user_media(user_id))
    APIAssertions(response).status(401)


# ── GET /v1/users/mentionable ─────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_POST_API_033_get_mentionable_users(post_token):
    """TC-POST-API-033 | Smoke | Get mentionable users typeahead returns 200"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.MENTIONABLE,
            params={"query": "test"},
            headers={"Authorization": f"Bearer {post_token}"},
        )
    APIAssertions(response).status(200)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_POST_API_034_get_mentionable_no_token():
    """TC-POST-API-034 | Security | Mentionable without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.MENTIONABLE,
            params={"query": "test"},
        )
    APIAssertions(response).status(401)


# ── DELETE /v1/posts/:post_id (last — deletes the fixture post) ───────────────

@pytest.mark.negative
@pytest.mark.api
async def test_TC_POST_API_035_delete_post_no_token(created_post_id):
    """TC-POST-API-035 | Security | Delete post without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.delete(APIEndpoints.post_detail(created_post_id))
    APIAssertions(response).status(401)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_POST_API_036_delete_post_not_found(post_token):
    """TC-POST-API-036 | Negative | Delete nonexistent post returns 403/404"""
    async with HonoAPIClient() as client:
        response = await client.delete(
            APIEndpoints.post_detail(NONEXISTENT_POST_ID),
            headers={"Authorization": f"Bearer {post_token}"},
        )
    APIAssertions(response).status_in(403, 404)


@pytest.mark.smoke
@pytest.mark.api
async def test_TC_POST_API_037_delete_post_valid(post_token, created_post_id):
    """TC-POST-API-037 | Smoke | Delete own post returns 200/204 (runs last)"""
    async with HonoAPIClient() as client:
        response = await client.delete(
            APIEndpoints.post_detail(created_post_id),
            headers={"Authorization": f"Bearer {post_token}"},
        )
    APIAssertions(response).status_in(200, 204)
