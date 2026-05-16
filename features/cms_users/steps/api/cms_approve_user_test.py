"""CMS Approve User API Tests — POST /v1/users/:id/approve."""
import allure
import pytest
import time

from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator
from skills.testing.helpers import skip_on_email_quota
from features.register.test_data.register_test_data import RegisterTestData
from core.db.db_client import DBClient

pytestmark = allure.feature("CMS Approve User")


async def _register_new_user() -> dict:
    payload = RegisterTestData.valid_payload()
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/register", json=payload)
    skip_on_email_quota(response)
    assert response.status_code == 200, \
        f"Register failed: {response.status_code} {response.json()}"
    return payload


@allure.story("TC-CMS-APPROVE-001: Full flow register → verify → approve")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.asyncio
async def test_TC_CMS_APPROVE_001_full_flow_register_verify_approve(cms_token):
    """
    TC-CMS-APPROVE-001 | Smoke | Full E2E flow
    Register → DB set verified → CMS approve → Verify APPROVED in DB
    """
    payload = await _register_new_user()
    email = payload["email"]

    time.sleep(1)
    with DBClient() as db:
        user = db.get_user_by_email(email)
    assert user, f"User not found in DB: {email}"
    assert user["status"] == "PENDING"
    user_id = user["id"]

    with DBClient() as db:
        assert db.set_verified(email), f"Failed to set verified for: {email}"

    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {cms_token}"
        response = await client.post(f"/v1/users/{user_id}/approve")
    assert response.status_code == 200, \
        f"Approve failed: {response.status_code} {response.json()}"

    time.sleep(1)
    with DBClient() as db:
        updated = db.get_user_by_email(email)
    assert updated["status"] == "APPROVED", f"Expected APPROVED, got: {updated['status']}"
    assert updated["approved_at"] is not None


@allure.story("TC-CMS-APPROVE-002: Approve unverified user")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_TC_CMS_APPROVE_002_approve_without_verification(cms_token):
    """
    TC-CMS-APPROVE-002 | Negative | Approve PENDING user (not verified)
    """
    payload = await _register_new_user()
    time.sleep(1)
    with DBClient() as db:
        user = db.get_user_by_email(payload["email"])
    assert user["status"] == "PENDING"

    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {cms_token}"
        response = await client.post(f"/v1/users/{user['id']}/approve")
    assert response.status_code in [200, 400, 422]


@allure.story("TC-CMS-APPROVE-003: Approve nonexistent user")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_TC_CMS_APPROVE_003_approve_nonexistent_user(cms_token):
    """TC-CMS-APPROVE-003 | Negative | Approve with invalid user ID"""
    fake_id = "00000000-0000-0000-0000-000000000000"
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {cms_token}"
        response = await client.post(f"/v1/users/{fake_id}/approve")
    assert response.status_code in [404, 400]


@allure.story("TC-CMS-APPROVE-004: Approve without token")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.asyncio
async def test_TC_CMS_APPROVE_004_approve_without_token():
    """TC-CMS-APPROVE-004 | Security | Approve without CMS token"""
    with DBClient() as db:
        user = db.get_latest_pending_user()
    if not user:
        pytest.skip("No pending users in DB")
    async with HonoAPIClient() as client:
        response = await client.post(f"/v1/users/{user['id']}/approve")
    assert response.status_code == 401


@allure.story("TC-CMS-APPROVE-005: Approve already approved user")
@allure.severity(allure.severity_level.MINOR)
@pytest.mark.asyncio
async def test_TC_CMS_APPROVE_005_approve_already_approved(cms_token):
    """TC-CMS-APPROVE-005 | Boundary | Approve already approved user"""
    with DBClient() as db:
        with db._conn.cursor() as cur:
            cur.execute("""
                SELECT BIN_TO_UUID(id) as id, email, status
                FROM users WHERE status = 'APPROVED'
                ORDER BY approved_at DESC LIMIT 1
            """)
            user = cur.fetchone()
    if not user:
        pytest.skip("No approved users in DB")
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {cms_token}"
        response = await client.post(f"/v1/users/{user['id']}/approve")
    assert response.status_code in [200, 400, 409]
