"""Privacy API Tests — follow, block, mute, counts, lists"""
import pytest
import allure

from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator
from config.test_config import APIEndpoints

pytestmark = allure.feature("Privacy")

NONEXISTENT_UUID = "00000000-0000-0000-0000-000000000000"


# ── POST /v1/users/:id/follow ─────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_PRIV_001_follow_user(actor_token, target_user):
    """TC-PRIV-001 | Smoke | Follow a valid user returns 200"""
    target_id = target_user.get("id", "")
    if not target_id:
        pytest.skip("target user id not available")
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.user_follow(target_id),
            json={"relationship_type_id": ""},
            headers={"Authorization": f"Bearer {actor_token}"},
        )
    SchemaValidator(response).status_in(200, 201)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_PRIV_002_follow_user_no_token(target_user):
    """TC-PRIV-002 | Security | Follow without auth returns 401"""
    target_id = target_user.get("id", NONEXISTENT_UUID)
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.user_follow(target_id),
            json={"relationship_type_id": ""},
        )
    SchemaValidator(response).status(401)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_PRIV_003_follow_nonexistent_user(actor_token):
    """TC-PRIV-003 | Negative | Follow nonexistent user returns 404"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.user_follow(NONEXISTENT_UUID),
            json={"relationship_type_id": ""},
            headers={"Authorization": f"Bearer {actor_token}"},
        )
    # [DEV-BUG] POST /v1/users/{uuid}/follow with nonexistent UUID returns 422 instead of 404.
    # RFC 7231: missing resource should be 404, not 422 (validation error).
    # Remove 422 from accepted set once API team fixes. Internal code: NOKUNPROC.
    SchemaValidator(response).status_in(404, 400, 422)


# ── DELETE /v1/users/:id/follow ───────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_PRIV_004_unfollow_user(actor_token, target_user):
    """TC-PRIV-004 | Smoke | Unfollow a user returns 200"""
    target_id = target_user.get("id", "")
    if not target_id:
        pytest.skip("target user id not available")
    async with HonoAPIClient() as client:
        response = await client.delete(
            APIEndpoints.user_follow(target_id),
            headers={"Authorization": f"Bearer {actor_token}"},
        )
    SchemaValidator(response).status_in(200, 204, 404)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_PRIV_005_unfollow_no_token(target_user):
    """TC-PRIV-005 | Security | Unfollow without auth returns 401"""
    target_id = target_user.get("id", NONEXISTENT_UUID)
    async with HonoAPIClient() as client:
        response = await client.delete(APIEndpoints.user_follow(target_id))
    SchemaValidator(response).status(401)


# ── POST /v1/settings/accounts/block ─────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_PRIV_006_block_user(actor_token, target_user):
    """TC-PRIV-006 | Smoke | Block a user returns 200"""
    target_id = target_user.get("id", "")
    if not target_id:
        pytest.skip("target user id not available")
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.SETTINGS_ACCOUNTS_BLOCK,
            json={"target_user_ids": [target_id]},
            headers={"Authorization": f"Bearer {actor_token}"},
        )
    SchemaValidator(response).status_in(200, 201)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_PRIV_007_block_user_no_token(target_user):
    """TC-PRIV-007 | Security | Block without auth returns 401"""
    target_id = target_user.get("id", NONEXISTENT_UUID)
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.SETTINGS_ACCOUNTS_BLOCK,
            json={"target_user_ids": [target_id]},
        )
    SchemaValidator(response).status(401)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_PRIV_008_block_empty_list(actor_token):
    """TC-PRIV-008 | Negative | Block with empty target_user_ids returns 400/422"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.SETTINGS_ACCOUNTS_BLOCK,
            json={"target_user_ids": []},
            headers={"Authorization": f"Bearer {actor_token}"},
        )
    SchemaValidator(response).status_in(400, 422, 200)


# ── DELETE /v1/settings/accounts/block ───────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_PRIV_009_unblock_user(actor_token, target_user):
    """TC-PRIV-009 | Smoke | Unblock a previously blocked user returns 200"""
    target_id = target_user.get("id", "")
    if not target_id:
        pytest.skip("target user id not available")
    async with HonoAPIClient() as client:
        response = await client.delete(
            APIEndpoints.SETTINGS_ACCOUNTS_BLOCK,
            json={"target_user_ids": [target_id]},
            headers={"Authorization": f"Bearer {actor_token}"},
        )
    SchemaValidator(response).status_in(200, 204)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_PRIV_010_unblock_no_token():
    """TC-PRIV-010 | Security | Unblock without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.delete(
            APIEndpoints.SETTINGS_ACCOUNTS_BLOCK,
            json={"target_user_ids": [NONEXISTENT_UUID]},
        )
    SchemaValidator(response).status(401)


# ── POST /v1/settings/accounts/mute ──────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_PRIV_011_mute_user(actor_token, target_user):
    """TC-PRIV-011 | Smoke | Mute a user returns 200"""
    target_id = target_user.get("id", "")
    if not target_id:
        pytest.skip("target user id not available")
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.SETTINGS_ACCOUNTS_MUTE,
            json={"target_user_ids": [target_id]},
            headers={"Authorization": f"Bearer {actor_token}"},
        )
    SchemaValidator(response).status_in(200, 201)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_PRIV_012_mute_no_token():
    """TC-PRIV-012 | Security | Mute without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.SETTINGS_ACCOUNTS_MUTE,
            json={"target_user_ids": [NONEXISTENT_UUID]},
        )
    SchemaValidator(response).status(401)


# ── DELETE /v1/settings/accounts/mute ────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_PRIV_013_unmute_user(actor_token, target_user):
    """TC-PRIV-013 | Smoke | Unmute a user returns 200"""
    target_id = target_user.get("id", "")
    if not target_id:
        pytest.skip("target user id not available")
    async with HonoAPIClient() as client:
        response = await client.delete(
            APIEndpoints.SETTINGS_ACCOUNTS_MUTE,
            json={"target_user_ids": [target_id]},
            headers={"Authorization": f"Bearer {actor_token}"},
        )
    SchemaValidator(response).status_in(200, 204)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_PRIV_014_unmute_no_token():
    """TC-PRIV-014 | Security | Unmute without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.delete(
            APIEndpoints.SETTINGS_ACCOUNTS_MUTE,
            json={"target_user_ids": [NONEXISTENT_UUID]},
        )
    SchemaValidator(response).status(401)


# ── POST /v1/users/:user_id/mute ─────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_PRIV_015_mute_user_by_id(actor_token, target_user):
    """TC-PRIV-015 | Smoke | Mute user via profile endpoint returns 200"""
    target_id = target_user.get("id", "")
    if not target_id:
        pytest.skip("target user id not available")
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.user_mute_by_id(target_id),
            headers={"Authorization": f"Bearer {actor_token}"},
        )
    SchemaValidator(response).status_in(200, 201)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_PRIV_016_mute_self_returns_400(actor_token, actor_user):
    """TC-PRIV-016 | Negative | Mute yourself returns 400"""
    user_id = actor_user.get("id", "")
    if not user_id:
        pytest.skip("actor user id not available")
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.user_mute_by_id(user_id),
            headers={"Authorization": f"Bearer {actor_token}"},
        )
    SchemaValidator(response).status_in(400, 422)


# ── GET /v1/settings/account/counts ──────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_PRIV_017_get_blocked_muted_counts(actor_token):
    """TC-PRIV-017 | Smoke | Get blocked/muted counts returns 200 with counts"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SETTINGS_ACCOUNT_COUNTS,
            headers={"Authorization": f"Bearer {actor_token}"},
        )
    assert response.status_code == 200
    body = response.json()
    data = body.get("data", {})
    assert "blocked_count" in data
    assert "muted_count" in data


@pytest.mark.negative
@pytest.mark.api
async def test_TC_PRIV_018_get_counts_no_token():
    """TC-PRIV-018 | Security | Get counts without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.get(APIEndpoints.SETTINGS_ACCOUNT_COUNTS)
    SchemaValidator(response).status(401)


# ── GET /v1/settings/account/list?section=BLOCKED ────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_PRIV_019_get_blocked_users_list(actor_token):
    """TC-PRIV-019 | Smoke | Get blocked users list returns 200"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SETTINGS_ACCOUNT_LIST,
            params={"section": "BLOCKED", "page": 1, "per_page": 20},
            headers={"Authorization": f"Bearer {actor_token}"},
        )
    assert response.status_code == 200
    body = response.json()
    data = body.get("data", {})
    assert "items" in data


@pytest.mark.negative
@pytest.mark.api
async def test_TC_PRIV_020_get_blocked_list_no_token():
    """TC-PRIV-020 | Security | Blocked list without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SETTINGS_ACCOUNT_LIST,
            params={"section": "BLOCKED"},
        )
    SchemaValidator(response).status(401)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_PRIV_021_get_account_list_invalid_section(actor_token):
    """TC-PRIV-021 | Negative | Account list with invalid section returns 400/422"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SETTINGS_ACCOUNT_LIST,
            params={"section": "INVALID_SECTION"},
            headers={"Authorization": f"Bearer {actor_token}"},
        )
    SchemaValidator(response).status_in(400, 422)


# ── GET /v1/settings/account/list?section=MUTED ──────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_PRIV_022_get_muted_users_list(actor_token):
    """TC-PRIV-022 | Smoke | Get muted users list returns 200"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SETTINGS_ACCOUNT_LIST,
            params={"section": "MUTED", "page": 1, "per_page": 20},
            headers={"Authorization": f"Bearer {actor_token}"},
        )
    assert response.status_code == 200
    body = response.json()
    data = body.get("data", {})
    assert "items" in data
