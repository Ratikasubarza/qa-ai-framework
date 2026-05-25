"""Privacy & Safety API Tests — block, unblock, mute, unmute, get blocked/muted lists."""
import pytest
import allure

from config.test_config import APIEndpoints
from config.test_data import BoundaryValues
from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator

pytestmark = [allure.feature("Privacy Safety"), allure.suite("API")]


# ── POST /v1/settings/accounts/block ─────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_001_block_single_user(auth_token, target_users):
    """TC-PS-001 | Smoke | Block a single user returns 200 with OK code"""
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.post(
            APIEndpoints.SETTINGS_ACCOUNTS_BLOCK,
            json={"target_user_ids": [target_users[0]]},
        )
    SchemaValidator(response).status(200).code_equals("OK")


@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_002_block_multiple_users_bulk(auth_token, target_users):
    """TC-PS-002 | Smoke | Block 2 users in a single bulk request returns 200"""
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.post(
            APIEndpoints.SETTINGS_ACCOUNTS_BLOCK,
            json={"target_user_ids": target_users},
        )
    SchemaValidator(response).status(200)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_003_block_already_blocked_user_idempotent(auth_token, target_users):
    """TC-PS-003 | Negative | Re-blocking an already-blocked user returns 200 or 422"""
    # target_users[0] was blocked in TC-PS-002 (smoke runs before negative)
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.post(
            APIEndpoints.SETTINGS_ACCOUNTS_BLOCK,
            json={"target_user_ids": [target_users[0]]},
        )
    SchemaValidator(response).status_in(200, 422)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_004_block_self_returns_400(auth_token, registered_user):
    """TC-PS-004 | Negative | Blocking own user_id returns 400"""
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.post(
            APIEndpoints.SETTINGS_ACCOUNTS_BLOCK,
            json={"target_user_ids": [registered_user["user_id"]]},
        )
    SchemaValidator(response).status(400)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_005_block_nonexistent_user_returns_404(auth_token):
    """TC-PS-005 | Negative | Blocking a non-existent UUID returns 404"""
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.post(
            APIEndpoints.SETTINGS_ACCOUNTS_BLOCK,
            json={"target_user_ids": [BoundaryValues.NON_EXISTENT_UUID]},
        )
    SchemaValidator(response).status(404)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_006_block_missing_field_returns_422(auth_token):
    """TC-PS-006 | Negative | Block request with missing target_user_ids field returns 422"""
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.post(
            APIEndpoints.SETTINGS_ACCOUNTS_BLOCK,
            json={},
        )
    SchemaValidator(response).status(422)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_007_block_empty_array_returns_422(auth_token):
    """TC-PS-007 | Negative | Block request with empty target_user_ids array returns 422"""
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.post(
            APIEndpoints.SETTINGS_ACCOUNTS_BLOCK,
            json={"target_user_ids": []},
        )
    SchemaValidator(response).status(422)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_008_block_no_auth_returns_401():
    """TC-PS-008 | Security | Block request without auth token returns 401"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.SETTINGS_ACCOUNTS_BLOCK,
            json={"target_user_ids": [BoundaryValues.NON_EXISTENT_UUID]},
        )
    SchemaValidator(response).status(401)


# ── DELETE /v1/settings/accounts/block ───────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_009_unblock_single_user(auth_token, target_users):
    """TC-PS-009 | Smoke | Unblock a single user returns 200"""
    # target_users[0] is blocked from TC-PS-002; unblock it here
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.delete(
            APIEndpoints.SETTINGS_ACCOUNTS_BLOCK,
            json={"target_user_ids": [target_users[0]]},
        )
    SchemaValidator(response).status(200)


@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_010_unblock_multiple_users_bulk(auth_token, target_users):
    """TC-PS-010 | Smoke | Unblock 2 users in bulk returns 200"""
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.delete(
            APIEndpoints.SETTINGS_ACCOUNTS_BLOCK,
            json={"target_user_ids": target_users},
        )
    SchemaValidator(response).status(200)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_011_unblock_not_blocked_user(auth_token, target_users):
    """TC-PS-011 | Negative | Unblocking a user who is not blocked returns 200 or 404"""
    # Both users are unblocked after TC-PS-010
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.delete(
            APIEndpoints.SETTINGS_ACCOUNTS_BLOCK,
            json={"target_user_ids": [target_users[0]]},
        )
    SchemaValidator(response).status_in(200, 404)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_012_unblock_empty_array_returns_422(auth_token):
    """TC-PS-012 | Negative | Unblock request with empty array returns 422"""
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.delete(
            APIEndpoints.SETTINGS_ACCOUNTS_BLOCK,
            json={"target_user_ids": []},
        )
    SchemaValidator(response).status(422)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_013_unblock_no_auth_returns_401():
    """TC-PS-013 | Security | Unblock request without auth token returns 401"""
    async with HonoAPIClient() as client:
        response = await client.delete(
            APIEndpoints.SETTINGS_ACCOUNTS_BLOCK,
            json={"target_user_ids": [BoundaryValues.NON_EXISTENT_UUID]},
        )
    SchemaValidator(response).status(401)


# ── POST /v1/settings/accounts/mute ──────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_014_mute_single_user(auth_token, target_users):
    """TC-PS-014 | Smoke | Mute a single user returns 200 with OK code"""
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.post(
            APIEndpoints.SETTINGS_ACCOUNTS_MUTE,
            json={"target_user_ids": [target_users[0]]},
        )
    SchemaValidator(response).status(200).code_equals("OK")


@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_015_mute_multiple_users_bulk(auth_token, target_users):
    """TC-PS-015 | Smoke | Mute 2 users in a single bulk request returns 200"""
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.post(
            APIEndpoints.SETTINGS_ACCOUNTS_MUTE,
            json={"target_user_ids": target_users},
        )
    SchemaValidator(response).status(200)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_016_mute_already_muted_user_idempotent(auth_token, target_users):
    """TC-PS-016 | Negative | Re-muting an already-muted user returns 200 or 422"""
    # target_users[0] was muted in TC-PS-015 (smoke runs before negative)
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.post(
            APIEndpoints.SETTINGS_ACCOUNTS_MUTE,
            json={"target_user_ids": [target_users[0]]},
        )
    SchemaValidator(response).status_in(200, 422)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_017_mute_nonexistent_user_returns_404(auth_token):
    """TC-PS-017 | Negative | Muting a non-existent UUID returns 404"""
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.post(
            APIEndpoints.SETTINGS_ACCOUNTS_MUTE,
            json={"target_user_ids": [BoundaryValues.NON_EXISTENT_UUID]},
        )
    SchemaValidator(response).status(404)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_018_mute_missing_field_returns_422(auth_token):
    """TC-PS-018 | Negative | Mute request with missing target_user_ids field returns 422"""
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.post(
            APIEndpoints.SETTINGS_ACCOUNTS_MUTE,
            json={},
        )
    SchemaValidator(response).status(422)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_019_mute_no_auth_returns_401():
    """TC-PS-019 | Security | Mute request without auth token returns 401"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.SETTINGS_ACCOUNTS_MUTE,
            json={"target_user_ids": [BoundaryValues.NON_EXISTENT_UUID]},
        )
    SchemaValidator(response).status(401)


# ── DELETE /v1/settings/accounts/mute ────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_020_unmute_single_user(auth_token, target_users):
    """TC-PS-020 | Smoke | Unmute a single user returns 200"""
    # target_users[0] is muted from TC-PS-015; unmute it here
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.delete(
            APIEndpoints.SETTINGS_ACCOUNTS_MUTE,
            json={"target_user_ids": [target_users[0]]},
        )
    SchemaValidator(response).status(200)


@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_021_unmute_multiple_users_bulk(auth_token, target_users):
    """TC-PS-021 | Smoke | Unmute 2 users in bulk returns 200"""
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.delete(
            APIEndpoints.SETTINGS_ACCOUNTS_MUTE,
            json={"target_user_ids": target_users},
        )
    SchemaValidator(response).status(200)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_022_unmute_not_muted_user(auth_token, target_users):
    """TC-PS-022 | Negative | Unmuting a user who is not muted returns 200 or 404"""
    # Both users are unmuted after TC-PS-021
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.delete(
            APIEndpoints.SETTINGS_ACCOUNTS_MUTE,
            json={"target_user_ids": [target_users[0]]},
        )
    SchemaValidator(response).status_in(200, 404)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_023_unmute_no_auth_returns_401():
    """TC-PS-023 | Security | Unmute request without auth token returns 401"""
    async with HonoAPIClient() as client:
        response = await client.delete(
            APIEndpoints.SETTINGS_ACCOUNTS_MUTE,
            json={"target_user_ids": [BoundaryValues.NON_EXISTENT_UUID]},
        )
    SchemaValidator(response).status(401)


# ── GET /v1/settings/account/list?section=BLOCKED ────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_024_get_blocked_list_returns_results(auth_token, target_users):
    """TC-PS-024 | Smoke | Get blocked list returns 200 with at least one entry and valid schema"""
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        await client.post(
            APIEndpoints.SETTINGS_ACCOUNTS_BLOCK,
            json={"target_user_ids": [target_users[0]]},
        )

    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.get(
            APIEndpoints.SETTINGS_ACCOUNT_LIST,
            params={"section": "BLOCKED"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body.get("code") == "OK"
    data = body.get("data", [])
    assert isinstance(data, list)
    assert len(data) >= 1
    item = data[0]
    for field in ("id", "name", "is_verified"):
        assert field in item, f"Missing field '{field}' in blocked list item"


@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_025_get_blocked_list_empty_after_unblock(auth_token, target_users):
    """TC-PS-025 | Smoke | Blocked list is empty after all target users are unblocked"""
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        await client.delete(
            APIEndpoints.SETTINGS_ACCOUNTS_BLOCK,
            json={"target_user_ids": target_users},
        )

    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.get(
            APIEndpoints.SETTINGS_ACCOUNT_LIST,
            params={"section": "BLOCKED"},
        )

    assert response.status_code == 200
    body = response.json()
    data = body.get("data", [])
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_026_get_blocked_list_search_param(auth_token, target_users):
    """TC-PS-026 | Functional | Blocked list with q= search param returns 200"""
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        await client.post(
            APIEndpoints.SETTINGS_ACCOUNTS_BLOCK,
            json={"target_user_ids": [target_users[0]]},
        )

    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.get(
            APIEndpoints.SETTINGS_ACCOUNT_LIST,
            params={"section": "BLOCKED", "q": "a"},
        )

    SchemaValidator(response).status(200)


@pytest.mark.boundary
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_027_get_blocked_list_pagination(auth_token, target_users):
    """TC-PS-027 | Boundary | Blocked list with pagination params returns 200"""
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.get(
            APIEndpoints.SETTINGS_ACCOUNT_LIST,
            params={"section": "BLOCKED", "page": 1, "per_page": 5},
        )
    SchemaValidator(response).status(200)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_028_get_blocked_list_invalid_section_returns_422(auth_token):
    """TC-PS-028 | Negative | Account list with invalid section returns 422"""
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.get(
            APIEndpoints.SETTINGS_ACCOUNT_LIST,
            params={"section": "INVALID_SECTION"},
        )
    SchemaValidator(response).status(422)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_029_get_blocked_list_no_auth_returns_401():
    """TC-PS-029 | Security | Get blocked list without auth token returns 401"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SETTINGS_ACCOUNT_LIST,
            params={"section": "BLOCKED"},
        )
    SchemaValidator(response).status(401)


# ── GET /v1/settings/account/list?section=MUTED ──────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_030_get_muted_list_returns_results(auth_token, target_users):
    """TC-PS-030 | Smoke | Get muted list returns 200 with at least one entry"""
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        await client.post(
            APIEndpoints.SETTINGS_ACCOUNTS_MUTE,
            json={"target_user_ids": [target_users[0]]},
        )

    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.get(
            APIEndpoints.SETTINGS_ACCOUNT_LIST,
            params={"section": "MUTED"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body.get("code") == "OK"
    data = body.get("data", [])
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_031_get_muted_list_empty_after_unmute(auth_token, target_users):
    """TC-PS-031 | Smoke | Muted list is empty after all target users are unmuted"""
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        await client.delete(
            APIEndpoints.SETTINGS_ACCOUNTS_MUTE,
            json={"target_user_ids": target_users},
        )

    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.get(
            APIEndpoints.SETTINGS_ACCOUNT_LIST,
            params={"section": "MUTED"},
        )

    assert response.status_code == 200
    body = response.json()
    data = body.get("data", [])
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_032_get_muted_list_search_param(auth_token, target_users):
    """TC-PS-032 | Functional | Muted list with q= search param returns 200"""
    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        await client.post(
            APIEndpoints.SETTINGS_ACCOUNTS_MUTE,
            json={"target_user_ids": [target_users[0]]},
        )

    async with HonoAPIClient() as client:
        client.set_auth_token(auth_token)
        response = await client.get(
            APIEndpoints.SETTINGS_ACCOUNT_LIST,
            params={"section": "MUTED", "q": "a"},
        )

    SchemaValidator(response).status(200)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PS_033_get_muted_list_no_auth_returns_401():
    """TC-PS-033 | Security | Get muted list without auth token returns 401"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SETTINGS_ACCOUNT_LIST,
            params={"section": "MUTED"},
        )
    SchemaValidator(response).status(401)
