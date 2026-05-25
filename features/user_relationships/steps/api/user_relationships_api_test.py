"""User Relationships API Tests — follow endpoint."""
import pytest
import allure

from config.test_config import APIEndpoints
from config.test_data import BoundaryValues
from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator

pytestmark = [
    allure.feature("User Relationships"),
    allure.suite("API"),
]


# ── POST /v1/users/:id/follow ─────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_UR_001_follow_user_success(authenticated_client, follow_target):
    """TC-UR-001 | Smoke | Follow a user returns 200 or 201 — documents API behavior"""
    # relationship_type_id is optional/nullable per Bruno contract (annotation error).
    # This test discovers actual response shape — do not hard-fail on code value.
    resp = await authenticated_client.post(
        APIEndpoints.user_follow(follow_target),
        json={"relationship_type_id": ""},
    )
    SchemaValidator(resp).status_in(200, 201).attach_to_report("follow_user_success")


@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_UR_002_follow_user_already_followed(authenticated_client, follow_target):
    """TC-UR-002 | Smoke | Re-following a user returns 200 (idempotent) or 409 (conflict)"""
    await authenticated_client.post(
        APIEndpoints.user_follow(follow_target),
        json={"relationship_type_id": ""},
    )
    resp = await authenticated_client.post(
        APIEndpoints.user_follow(follow_target),
        json={"relationship_type_id": ""},
    )
    SchemaValidator(resp).status_in(200, 409).attach_to_report("follow_already_followed")


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_UR_003_follow_user_cannot_follow_self(registered_user, authenticated_client):
    """TC-UR-003 | Negative | Following own user_id returns 400"""
    resp = await authenticated_client.post(
        APIEndpoints.user_follow(registered_user["user_id"]),
        json={"relationship_type_id": ""},
    )
    SchemaValidator(resp).status(400).attach_to_report("follow_self_rejected")


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_UR_004_follow_user_target_not_found(authenticated_client):
    """TC-UR-004 | Negative | Follow with non-existent user_id returns 404"""
    resp = await authenticated_client.post(
        APIEndpoints.user_follow(BoundaryValues.NON_EXISTENT_UUID),
        json={"relationship_type_id": ""},
    )
    SchemaValidator(resp).status(404)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_UR_005_follow_user_invalid_uuid_format(authenticated_client):
    """TC-UR-005 | Negative | Follow with non-UUID path param returns 422"""
    resp = await authenticated_client.post(
        APIEndpoints.user_follow("not-a-valid-uuid"),
        json={"relationship_type_id": ""},
    )
    SchemaValidator(resp).status(422)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_UR_006_follow_user_no_auth(follow_target):
    """TC-UR-006 | Security | Follow without auth token returns 401"""
    async with HonoAPIClient() as client:
        resp = await client.post(
            APIEndpoints.user_follow(follow_target),
            json={"relationship_type_id": ""},
        )
    SchemaValidator(resp).status(401)
