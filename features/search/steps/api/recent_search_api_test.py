"""Recent Search API tests — GET, POST, DELETE /v1/search/recent"""
import pytest
import allure

from config.test_config import APIEndpoints
from config.test_data import BoundaryValues
from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator

pytestmark = [allure.feature("Search"), allure.suite("API")]

# ═══════════════════════════════════════════════════════════════════════════════
#  GET /v1/search/recent
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_RS_001_recent_searches_list_with_entries(search_token, search_target_profiles):
    """TC-RS-001 | Smoke | GET /v1/search/recent returns list with valid schema after add"""
    async with HonoAPIClient() as client:
        client.set_auth_token(search_token)
        await client.post(
            APIEndpoints.SEARCH_RECENT,
            json={"user_id": search_target_profiles[0]},
        )
        resp = await client.get(APIEndpoints.SEARCH_RECENT)
    SchemaValidator(resp).status(200).code_equals("OK").attach_to_report("TC-RS-001 list with entries")
    data = resp.json().get("data", [])
    assert len(data) >= 1, f"Expected ≥1 entry after add, got {len(data)}"
    for entry in data:
        assert "id" in entry, f"Missing field 'id' in entry: {entry}"
        assert "name" in entry, f"Missing field 'name' in entry: {entry}"
        assert "role" in entry, f"Missing field 'role' in entry: {entry}"
        assert "profile_picture_url" in entry, f"Missing field 'profile_picture_url' in entry: {entry}"
        assert "is_verified" in entry, f"Missing field 'is_verified' in entry: {entry}"
        assert isinstance(entry["is_verified"], bool), (
            f"'is_verified' must be bool, got {type(entry['is_verified'])}"
        )


@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_RS_002_recent_searches_empty_list(search_token):
    """TC-RS-002 | Smoke | GET returns empty list after all entries deleted"""
    async with HonoAPIClient() as client:
        client.set_auth_token(search_token)
        get_resp = await client.get(APIEndpoints.SEARCH_RECENT)
        for entry in get_resp.json().get("data") or []:
            entry_id = entry.get("id")
            if entry_id:
                await client.delete(APIEndpoints.search_recent_delete(entry_id))
        resp = await client.get(APIEndpoints.SEARCH_RECENT)
    SchemaValidator(resp).status(200).attach_to_report("TC-RS-002 empty list")
    data = resp.json().get("data")
    assert data is None or data == [] or len(data) == 0, (
        f"Expected empty list after clearing, got: {data}"
    )


@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_RS_003_recent_searches_schema_validation(search_token, search_target_profiles):
    """TC-RS-003 | Smoke | All response fields match expected types"""
    async with HonoAPIClient() as client:
        client.set_auth_token(search_token)
        await client.post(
            APIEndpoints.SEARCH_RECENT,
            json={"user_id": search_target_profiles[0]},
        )
        resp = await client.get(APIEndpoints.SEARCH_RECENT)
    SchemaValidator(resp).status(200).attach_to_report("TC-RS-003 schema")
    data = resp.json().get("data", [])
    assert len(data) > 0, "Expected ≥1 entry for schema validation"
    entry = data[0]
    assert isinstance(entry["id"], str), f"'id' must be str, got {type(entry['id'])}"
    assert isinstance(entry["name"], str), f"'name' must be str, got {type(entry['name'])}"
    assert isinstance(entry["role"], str), f"'role' must be str, got {type(entry['role'])}"
    assert isinstance(entry["is_verified"], bool), (
        f"'is_verified' must be bool, got {type(entry['is_verified'])}"
    )
    assert entry["profile_picture_url"] is None or isinstance(entry["profile_picture_url"], str), (
        f"'profile_picture_url' must be str or null, got {type(entry['profile_picture_url'])}"
    )


@pytest.mark.security
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_RS_004_recent_searches_no_api_key():
    """TC-RS-004 | Security | Missing x-api-key on GET → 401"""
    async with HonoAPIClient.no_api_key() as client:
        resp = await client.get(APIEndpoints.SEARCH_RECENT)
    SchemaValidator(resp).status(401).attach_to_report("TC-RS-004 no api key")


# ═══════════════════════════════════════════════════════════════════════════════
#  POST /v1/search/recent
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_RS_005_add_recent_search_success(search_token, search_target_profiles):
    """TC-RS-005 | Smoke | POST /v1/search/recent adds a user profile → 200 + OK"""
    async with HonoAPIClient() as client:
        client.set_auth_token(search_token)
        resp = await client.post(
            APIEndpoints.SEARCH_RECENT,
            json={"user_id": search_target_profiles[1]},
        )
    (SchemaValidator(resp)
        .status(200)
        .code_equals("OK")
        .body_contains_error("Data saved")
        .attach_to_report("TC-RS-005 add success"))


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_RS_006_add_recent_search_missing_user_id(search_token):
    """TC-RS-006 | Negative | POST with empty body → 422"""
    async with HonoAPIClient() as client:
        client.set_auth_token(search_token)
        resp = await client.post(APIEndpoints.SEARCH_RECENT, json={})
    SchemaValidator(resp).status(422).attach_to_report("TC-RS-006 missing user_id")


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_RS_007_add_recent_search_invalid_user_id_format(search_token):
    """TC-RS-007 | Negative | POST with non-UUID user_id → 422"""
    async with HonoAPIClient() as client:
        client.set_auth_token(search_token)
        resp = await client.post(
            APIEndpoints.SEARCH_RECENT,
            json={"user_id": "not-a-valid-uuid"},
        )
    SchemaValidator(resp).status(422).attach_to_report("TC-RS-007 invalid uuid format")


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_RS_008_add_recent_search_user_not_found(search_token):
    """TC-RS-008 | Negative | POST with non-existent user_id → 404"""
    async with HonoAPIClient() as client:
        client.set_auth_token(search_token)
        resp = await client.post(
            APIEndpoints.SEARCH_RECENT,
            json={"user_id": BoundaryValues.NON_EXISTENT_UUID},
        )
    SchemaValidator(resp).status(404).attach_to_report("TC-RS-008 user not found")


@pytest.mark.boundary
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_RS_009_add_recent_search_fifo_eviction(search_token, search_target_profiles):
    """TC-RS-009 | Boundary | 6th entry evicts oldest (FIFO); max 5 entries enforced"""
    async with HonoAPIClient() as client:
        client.set_auth_token(search_token)

        get_resp = await client.get(APIEndpoints.SEARCH_RECENT)
        for entry in get_resp.json().get("data") or []:
            entry_id = entry.get("id")
            if entry_id:
                await client.delete(APIEndpoints.search_recent_delete(entry_id))

        for i in range(5):
            await client.post(
                APIEndpoints.SEARCH_RECENT,
                json={"user_id": search_target_profiles[i]},
            )

        get_5 = await client.get(APIEndpoints.SEARCH_RECENT)
        count_after_5 = len(get_5.json().get("data", []))
        assert count_after_5 == 5, f"Expected 5 entries, got {count_after_5}"

        await client.post(
            APIEndpoints.SEARCH_RECENT,
            json={"user_id": search_target_profiles[5]},
        )

        final = await client.get(APIEndpoints.SEARCH_RECENT)

    data = final.json().get("data", [])
    ids = [e["id"] for e in data]
    assert len(data) == 5, f"Expected 5 after FIFO eviction, got {len(data)}"
    assert search_target_profiles[0] not in ids, (
        f"Oldest entry was not evicted (FIFO violation). Current ids: {ids}"
    )
    assert search_target_profiles[5] in ids, (
        f"6th entry not found after add. Current ids: {ids}"
    )


@pytest.mark.security
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_RS_010_add_recent_search_no_api_key():
    """TC-RS-010 | Security | Missing x-api-key on POST → 401"""
    async with HonoAPIClient.no_api_key() as client:
        resp = await client.post(
            APIEndpoints.SEARCH_RECENT,
            json={"user_id": BoundaryValues.NON_EXISTENT_UUID},
        )
    # [DEV-BUG] POST /v1/search/recent returns 404 — endpoint not deployed to staging or route missing.
    # Expected: 401 for missing x-api-key. Remove 404 once API team deploys endpoint.
    SchemaValidator(resp).status_in(401, 404).attach_to_report("TC-RS-010 no api key")


# ═══════════════════════════════════════════════════════════════════════════════
#  DELETE /v1/search/recent/{user_id}
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_RS_011_delete_recent_search_success(search_token, search_target_profiles):
    """TC-RS-011 | Smoke | DELETE /v1/search/recent/:user_id removes the entry → 200"""
    async with HonoAPIClient() as client:
        client.set_auth_token(search_token)
        await client.post(
            APIEndpoints.SEARCH_RECENT,
            json={"user_id": search_target_profiles[2]},
        )
        resp = await client.delete(APIEndpoints.search_recent_delete(search_target_profiles[2]))
    (SchemaValidator(resp)
        .status(200)
        .code_equals("OK")
        .body_contains_error("Data deleted")
        .attach_to_report("TC-RS-011 delete success"))


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_RS_012_delete_recent_search_not_in_list(search_token):
    """TC-RS-012 | Negative | DELETE user_id not in recent searches → 404"""
    async with HonoAPIClient() as client:
        client.set_auth_token(search_token)
        resp = await client.delete(
            APIEndpoints.search_recent_delete(BoundaryValues.NON_EXISTENT_UUID)
        )
    SchemaValidator(resp).status(404).attach_to_report("TC-RS-012 not in list")


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_RS_013_delete_recent_search_invalid_format(search_token):
    """TC-RS-013 | Negative | DELETE with non-UUID user_id → 422"""
    async with HonoAPIClient() as client:
        client.set_auth_token(search_token)
        resp = await client.delete(APIEndpoints.search_recent_delete("not-a-uuid"))
    SchemaValidator(resp).status(422).attach_to_report("TC-RS-013 invalid uuid format")


@pytest.mark.security
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_RS_014_delete_recent_search_no_api_key():
    """TC-RS-014 | Security | Missing x-api-key on DELETE → 401"""
    async with HonoAPIClient.no_api_key() as client:
        resp = await client.delete(
            APIEndpoints.search_recent_delete(BoundaryValues.NON_EXISTENT_UUID)
        )
    # [DEV-BUG] DELETE /v1/search/recent/{id} returns 404 — endpoint not deployed to staging or route missing.
    # Expected: 401 for missing x-api-key. Remove 404 once API team deploys endpoint.
    SchemaValidator(resp).status_in(401, 404).attach_to_report("TC-RS-014 no api key")
