"""
CMS Reject User API Tests — POST /v1/users/:id/reject
Flow: Register → set_verified(DB) → Reject via CMS API → Verify status REJECTED

Notes for dev team (known issues found during testing):
- Marked with [DEV-BUG] where API behavior seems incorrect
- Marked with [FLAKY] where test may be environment-dependent
"""
import allure
import pytest
import time

from platforms.api.httpx_client import HonoAPIClient
from skills.testing.helpers import skip_on_email_quota
from features.register.test_data.register_test_data import RegisterTestData
from core.db.db_client import DBClient
from config.test_config import APIEndpoints

pytestmark = allure.feature("CMS Reject User")


async def _register_and_verify() -> dict:
    """Register new user + set_verified in DB. Ready for approve/reject."""
    payload = RegisterTestData.valid_payload()
    async with HonoAPIClient() as client:
        resp = await client.post(APIEndpoints.REGISTER, json=payload)
    skip_on_email_quota(resp)
    assert resp.status_code == 200, f"Register failed: {resp.json()}"
    time.sleep(1)
    with DBClient() as db:
        user = db.get_user_by_email(payload["email"])
        assert user, f"User not found: {payload['email']}"
        db.set_verified(payload["email"])
    return {"email": payload["email"], "user_id": user["id"]}


@allure.story("TC-CMS-REJECT-001: Full flow register → verify → reject")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.asyncio
async def test_TC_CMS_REJECT_001_reject_verified_user(cms_token):
    """
    TC-CMS-REJECT-001 | Smoke | Full flow: Register → Verify → Reject
    """
    user = await _register_and_verify()
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {cms_token}"
        response = await client.post(
            APIEndpoints.reject(user['user_id']),
            json={"reason": "Does not meet community standards"},
        )
    assert response.status_code == 200, \
        f"Expected 200, got: {response.status_code} {response.json()}"
    time.sleep(1)
    with DBClient() as db:
        updated = db.get_user_by_email(user["email"])
    assert updated["status"] == "REJECTED", f"Expected REJECTED, got: {updated['status']}"


@allure.story("TC-CMS-REJECT-002: Reject without reason body")
@allure.severity(allure.severity_level.MINOR)
@pytest.mark.asyncio
async def test_TC_CMS_REJECT_002_reject_without_reason(cms_token):
    """TC-CMS-REJECT-002 | Boundary | Reject without reason body"""
    user = await _register_and_verify()
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {cms_token}"
        response = await client.post(APIEndpoints.reject(user['user_id']), json={})
    assert response.status_code in [200, 400, 422]


@allure.story("TC-CMS-REJECT-003: Reject with empty string reason")
@allure.severity(allure.severity_level.MINOR)
@pytest.mark.asyncio
async def test_TC_CMS_REJECT_003_reject_with_empty_reason(cms_token):
    """TC-CMS-REJECT-003 | Boundary | Reject with empty string reason"""
    user = await _register_and_verify()
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {cms_token}"
        response = await client.post(
            APIEndpoints.reject(user['user_id']),
            json={"reason": ""},
        )
    assert response.status_code in [200, 400, 422]


@allure.story("TC-CMS-REJECT-004: Reject without token")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.asyncio
async def test_TC_CMS_REJECT_004_reject_without_token():
    """TC-CMS-REJECT-004 | Security | Reject without CMS token returns 401"""
    user = await _register_and_verify()
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.reject(user['user_id']),
            json={"reason": "Test reject no auth"},
        )
    assert response.status_code == 401


@allure.story("TC-CMS-REJECT-005: Reject nonexistent user")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_TC_CMS_REJECT_005_reject_nonexistent_user(cms_token):
    """TC-CMS-REJECT-005 | Negative | Reject with invalid user ID returns 404"""
    fake_id = "00000000-0000-0000-0000-000000000000"
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {cms_token}"
        response = await client.post(
            APIEndpoints.reject(fake_id),
            json={"reason": "Test invalid ID"},
        )
    assert response.status_code in [404, 400]


@allure.story("TC-CMS-REJECT-006: Reject already approved user")
@allure.severity(allure.severity_level.MINOR)
@pytest.mark.asyncio
async def test_TC_CMS_REJECT_006_reject_already_approved_user(cms_token):
    """
    TC-CMS-REJECT-006 | Boundary | Reject already approved user
    [DEV-BUG] Should this be allowed? Business rule unclear.
    """
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
        response = await client.post(
            APIEndpoints.reject(user['id']),
            json={"reason": "Test reject approved user"},
        )
    assert response.status_code in [200, 400, 409, 422]


@allure.story("TC-CMS-REJECT-007: Double reject (idempotent check)")
@allure.severity(allure.severity_level.MINOR)
@pytest.mark.asyncio
async def test_TC_CMS_REJECT_007_reject_already_rejected_user(cms_token):
    """
    TC-CMS-REJECT-007 | Boundary | Reject already rejected user
    [DEV-BUG] Double reject — should be idempotent or return error?
    """
    user = await _register_and_verify()
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {cms_token}"
        await client.post(APIEndpoints.reject(user['user_id']), json={"reason": "First reject"})
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {cms_token}"
        r2 = await client.post(APIEndpoints.reject(user['user_id']), json={"reason": "Second reject"})
    assert r2.status_code in [200, 400, 409]


@allure.story("TC-CMS-REJECT-008: Reject unverified PENDING user")
@allure.severity(allure.severity_level.MINOR)
@pytest.mark.asyncio
async def test_TC_CMS_REJECT_008_reject_pending_unverified_user(cms_token):
    """
    TC-CMS-REJECT-008 | Edge | Reject PENDING user (not verified yet)
    [DEV-BUG] Should admin be able to reject unverified users?
    """
    payload = RegisterTestData.valid_payload()
    async with HonoAPIClient() as client:
        resp = await client.post(APIEndpoints.REGISTER, json=payload)
    skip_on_email_quota(resp)
    assert resp.status_code == 200
    time.sleep(1)
    with DBClient() as db:
        user = db.get_user_by_email(payload["email"])
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {cms_token}"
        response = await client.post(
            APIEndpoints.reject(user['id']),
            json={"reason": "Reject unverified user"},
        )
    assert response.status_code in [200, 400, 422]


@allure.story("TC-CMS-REJECT-009: Reject with very long reason")
@allure.severity(allure.severity_level.MINOR)
@pytest.mark.asyncio
async def test_TC_CMS_REJECT_009_reject_with_very_long_reason(cms_token):
    """TC-CMS-REJECT-009 | Boundary | Very long rejection reason (1000+ chars)"""
    user = await _register_and_verify()
    long_reason = "This user does not meet our standards. " * 30
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {cms_token}"
        response = await client.post(
            APIEndpoints.reject(user['user_id']),
            json={"reason": long_reason},
        )
    assert response.status_code in [200, 400, 422]


@allure.story("TC-CMS-REJECT-010: Reject then approve same user")
@allure.severity(allure.severity_level.MINOR)
@pytest.mark.asyncio
async def test_TC_CMS_REJECT_010_reject_then_approve(cms_token):
    """
    TC-CMS-REJECT-010 | Combination | Reject then approve same user
    [DEV-BUG] Should rejected user be approvable? Business rule unclear.
    """
    user = await _register_and_verify()
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {cms_token}"
        await client.post(
            APIEndpoints.reject(user['user_id']),
            json={"reason": "Test reject then approve"},
        )
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {cms_token}"
        r2 = await client.post(APIEndpoints.approve(user['user_id']))
    assert r2.status_code in [200, 400, 409]
