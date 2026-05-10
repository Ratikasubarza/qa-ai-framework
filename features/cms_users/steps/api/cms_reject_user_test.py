"""
CMS Reject User API Tests — POST /v1/users/:id/reject
Flow: Register → set_verified(DB) → Reject via CMS API → Verify status REJECTED

Notes for dev team (known issues found during testing):
- Marked with [DEV-BUG] where API behavior seems incorrect
- Marked with [FLAKY] where test may be environment-dependent
"""
import pytest
import time
import httpx
import os
from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator
from features.register.test_data.register_test_data import RegisterTestData
from features.cms_login.test_data.cms_login_test_data import CmsLoginTestData
from core.db.db_client import DBClient


async def get_cms_token() -> str:
    async with HonoAPIClient() as client:
        response = await client.post(
            "/v1/users/login",
            json=CmsLoginTestData.valid_payload()
        )
    data = response.json()
    body = data.get("data", data)
    return body.get("accessToken") or body.get("token", "")


async def register_and_verify() -> dict:
    """Register new user + set_verified in DB. Ready for approve/reject."""
    payload = RegisterTestData.valid_payload()
    async with HonoAPIClient() as client:
        resp = await client.post("/v1/users/register", json=payload)
    assert resp.status_code == 200, f"Register failed: {resp.json()}"

    time.sleep(1)
    with DBClient() as db:
        user = db.get_user_by_email(payload["email"])
        assert user, f"User not found: {payload['email']}"
        db.set_verified(payload["email"])

    return {"email": payload["email"], "user_id": user["id"]}


# ── Core Reject Tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_TC_CMS_REJECT_001_reject_verified_user():
    """
    TC-CMS-REJECT-001 | Smoke | Full flow: Register → Verify → Reject
    Given: Verified user (not yet approved)
    When: CMS admin rejects with reason
    Then: 200 + status REJECTED in DB
    """
    user = await register_and_verify()
    print(f"\n✓ Verified user: {user['email']}")

    token = await get_cms_token()
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.post(
            f"/v1/users/{user['user_id']}/reject",
            json={"reason": "Does not meet community standards"}
        )

    print(f"✓ Reject response: {response.status_code} {response.json()}")
    assert response.status_code == 200, \
        f"Expected 200, got: {response.status_code} {response.json()}"

    # Verify in DB
    time.sleep(1)
    with DBClient() as db:
        updated = db.get_user_by_email(user["email"])
    assert updated["status"] == "REJECTED", \
        f"Expected REJECTED, got: {updated['status']}"
    print(f"✓ Status in DB: {updated['status']}")


@pytest.mark.asyncio
async def test_TC_CMS_REJECT_002_reject_without_reason():
    """
    TC-CMS-REJECT-002 | Boundary | Reject without reason body
    Note: API may accept empty reason or require it
    """
    user = await register_and_verify()
    token = await get_cms_token()

    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.post(
            f"/v1/users/{user['user_id']}/reject",
            json={}  # No reason
        )

    print(f"\n✓ Reject without reason: {response.status_code} {response.json()}")
    # Document actual behavior
    assert response.status_code in [200, 400, 422], \
        f"Unexpected: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_CMS_REJECT_003_reject_with_empty_reason():
    """
    TC-CMS-REJECT-003 | Boundary | Reject with empty string reason
    """
    user = await register_and_verify()
    token = await get_cms_token()

    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.post(
            f"/v1/users/{user['user_id']}/reject",
            json={"reason": ""}
        )

    print(f"\n✓ Empty reason: {response.status_code} {response.json()}")
    assert response.status_code in [200, 400, 422], \
        f"Unexpected: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_CMS_REJECT_004_reject_without_token():
    """
    TC-CMS-REJECT-004 | Security | Reject without CMS token returns 401
    """
    user = await register_and_verify()

    async with HonoAPIClient() as client:
        # No Authorization header
        response = await client.post(
            f"/v1/users/{user['user_id']}/reject",
            json={"reason": "Test reject no auth"}
        )

    assert response.status_code == 401, \
        f"Expected 401, got: {response.status_code}"
    print(f"\n✓ Unauthenticated blocked: {response.status_code}")


@pytest.mark.asyncio
async def test_TC_CMS_REJECT_005_reject_nonexistent_user():
    """
    TC-CMS-REJECT-005 | Negative | Reject with invalid user ID returns 404
    """
    token = await get_cms_token()
    fake_id = "00000000-0000-0000-0000-000000000000"

    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.post(
            f"/v1/users/{fake_id}/reject",
            json={"reason": "Test invalid ID"}
        )

    assert response.status_code in [404, 400], \
        f"Expected 404/400, got: {response.status_code}"
    print(f"\n✓ Invalid ID blocked: {response.status_code}")


@pytest.mark.asyncio
async def test_TC_CMS_REJECT_006_reject_already_approved_user():
    """
    TC-CMS-REJECT-006 | Boundary | Reject already approved user
    [DEV-BUG] Should this be allowed? Business rule unclear.
    Expected: 400 (cannot reject approved user) or 200 (idempotent)
    """
    with DBClient() as db:
        with db._conn.cursor() as cur:
            cur.execute("""
                SELECT BIN_TO_UUID(id) as id, email, status
                FROM users
                WHERE status = 'APPROVED'
                ORDER BY approved_at DESC
                LIMIT 1
            """)
            user = cur.fetchone()

    if not user:
        pytest.skip("No approved users in DB")

    token = await get_cms_token()
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.post(
            f"/v1/users/{user['id']}/reject",
            json={"reason": "Test reject approved user"}
        )

    print(f"\n[DEV-BUG?] Reject approved user: {response.status_code} {response.json()}")
    # Document actual — not assert, just observe
    assert response.status_code in [200, 400, 409, 422], \
        f"Unexpected: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_CMS_REJECT_007_reject_already_rejected_user():
    """
    TC-CMS-REJECT-007 | Boundary | Reject already rejected user (idempotent?)
    [DEV-BUG] Double reject — should be idempotent or return error?
    """
    user = await register_and_verify()
    token = await get_cms_token()

    # First reject
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        r1 = await client.post(
            f"/v1/users/{user['user_id']}/reject",
            json={"reason": "First reject"}
        )
    print(f"\n  First reject: {r1.status_code}")

    # Second reject
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        r2 = await client.post(
            f"/v1/users/{user['user_id']}/reject",
            json={"reason": "Second reject"}
        )
    print(f"  Second reject: {r2.status_code} {r2.json()}")
    assert r2.status_code in [200, 400, 409], \
        f"Unexpected double reject: {r2.status_code}"


@pytest.mark.asyncio
async def test_TC_CMS_REJECT_008_reject_pending_unverified_user():
    """
    TC-CMS-REJECT-008 | Edge | Reject PENDING user (not verified yet)
    [DEV-BUG] Should admin be able to reject unverified users?
    """
    payload = RegisterTestData.valid_payload()
    async with HonoAPIClient() as client:
        resp = await client.post("/v1/users/register", json=payload)
    assert resp.status_code == 200

    time.sleep(1)
    with DBClient() as db:
        user = db.get_user_by_email(payload["email"])
        # NOT calling set_verified — user stays PENDING

    token = await get_cms_token()
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.post(
            f"/v1/users/{user['id']}/reject",
            json={"reason": "Reject unverified user"}
        )

    print(f"\n[DEV-BUG?] Reject unverified PENDING user: {response.status_code} {response.json()}")
    assert response.status_code in [200, 400, 422], \
        f"Unexpected: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_CMS_REJECT_009_reject_with_very_long_reason():
    """
    TC-CMS-REJECT-009 | Boundary | Very long rejection reason (1000+ chars)
    """
    user = await register_and_verify()
    token = await get_cms_token()
    long_reason = "This user does not meet our standards. " * 30  # ~1200 chars

    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.post(
            f"/v1/users/{user['user_id']}/reject",
            json={"reason": long_reason}
        )

    print(f"\n✓ Long reason ({len(long_reason)} chars): {response.status_code}")
    assert response.status_code in [200, 400, 422], \
        f"Unexpected: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_CMS_REJECT_010_reject_then_approve():
    """
    TC-CMS-REJECT-010 | Combination | Reject then approve same user
    [DEV-BUG] Should rejected user be approvable? Business rule unclear.
    """
    user = await register_and_verify()
    token = await get_cms_token()

    # Reject first
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        r1 = await client.post(
            f"/v1/users/{user['user_id']}/reject",
            json={"reason": "Test reject then approve"}
        )
    print(f"\n  Reject: {r1.status_code}")

    # Then approve
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        r2 = await client.post(f"/v1/users/{user['user_id']}/approve")
    print(f"  Approve after reject: {r2.status_code} {r2.json()}")

    # Check final DB status
    time.sleep(1)
    with DBClient() as db:
        final = db.get_user_by_email(user["email"])
    print(f"  Final DB status: {final['status']}")
    assert r2.status_code in [200, 400, 409], \
        f"Unexpected: {r2.status_code}"
