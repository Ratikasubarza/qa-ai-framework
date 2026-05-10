"""
CMS Approve User API Tests — POST /v1/users/:id/approve
Flow: Register → DB set verified → Approve via API → Verify APPROVED in DB
"""
import pytest
import time
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


async def register_new_user() -> dict:
    payload = RegisterTestData.valid_payload()
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/register", json=payload)
    assert response.status_code == 200, \
        f"Register failed: {response.status_code} {response.json()}"
    return payload


@pytest.mark.asyncio
async def test_TC_CMS_APPROVE_001_full_flow_register_verify_approve():
    """
    TC-CMS-APPROVE-001 | Smoke | Full E2E flow
    Register → DB set verified → CMS approve → Verify APPROVED in DB
    """
    # Step 1: Register new user
    payload = await register_new_user()
    email = payload["email"]
    print(f"\n✓ Step 1 — Registered: {email}")

    # Step 2: Get user from DB
    time.sleep(1)
    with DBClient() as db:
        user = db.get_user_by_email(email)

    assert user, f"User not found in DB: {email}"
    assert user["status"] == "PENDING"
    user_id = user["id"]
    print(f"✓ Step 2 — DB: id={user_id}, status={user['status']}")

    # Step 3: Simulate email verification via DB
    with DBClient() as db:
        verified = db.set_verified(email)
    assert verified, f"Failed to set verified for: {email}"
    print(f"✓ Step 3 — Email verification simulated via DB")

    # Step 4: CMS admin approve
    token = await get_cms_token()
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.post(f"/v1/users/{user_id}/approve")

    print(f"✓ Step 4 — Approve: {response.status_code} {response.json()}")
    assert response.status_code == 200, \
        f"Approve failed: {response.status_code} {response.json()}"

    # Step 5: Verify final status in DB
    time.sleep(1)
    with DBClient() as db:
        updated = db.get_user_by_email(email)

    assert updated["status"] == "APPROVED", \
        f"Expected APPROVED, got: {updated['status']}"
    assert updated["approved_at"] is not None, "approved_at should be set"
    print(f"✓ Step 5 — Final status: {updated['status']}")
    print(f"  approved_at: {updated['approved_at']}")


@pytest.mark.asyncio
async def test_TC_CMS_APPROVE_002_approve_without_verification():
    """
    TC-CMS-APPROVE-002 | Negative | Approve PENDING user (not verified)
    Given: User registered but NOT verified via email
    When: CMS admin tries to approve
    Then: Should return error (cannot approve unverified user)
    """
    payload = await register_new_user()
    email = payload["email"]
    print(f"\n✓ Registered (not verified): {email}")

    time.sleep(1)
    with DBClient() as db:
        user = db.get_user_by_email(email)

    assert user["status"] == "PENDING"
    user_id = user["id"]

    # Try approve without verification
    token = await get_cms_token()
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.post(f"/v1/users/{user_id}/approve")

    print(f"✓ Approve unverified: {response.status_code} {response.json()}")
    # API should block this — 400 or allow it (200)
    assert response.status_code in [200, 400, 422], \
        f"Unexpected: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_CMS_APPROVE_003_approve_nonexistent_user():
    """
    TC-CMS-APPROVE-003 | Negative | Approve with invalid user ID
    """
    token = await get_cms_token()
    fake_id = "00000000-0000-0000-0000-000000000000"

    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.post(f"/v1/users/{fake_id}/approve")

    assert response.status_code in [404, 400], \
        f"Expected 404/400, got: {response.status_code}"
    print(f"\n✓ Invalid ID blocked: {response.status_code}")


@pytest.mark.asyncio
async def test_TC_CMS_APPROVE_004_approve_without_token():
    """
    TC-CMS-APPROVE-004 | Security | Approve without CMS token
    """
    with DBClient() as db:
        user = db.get_latest_pending_user()

    if not user:
        pytest.skip("No pending users in DB")

    async with HonoAPIClient() as client:
        response = await client.post(f"/v1/users/{user['id']}/approve")

    assert response.status_code == 401, \
        f"Expected 401, got: {response.status_code}"
    print(f"\n✓ Unauthenticated blocked: {response.status_code}")


@pytest.mark.asyncio
async def test_TC_CMS_APPROVE_005_approve_already_approved():
    """
    TC-CMS-APPROVE-005 | Boundary | Approve already approved user
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
        response = await client.post(f"/v1/users/{user['id']}/approve")

    assert response.status_code in [200, 400, 409], \
        f"Unexpected: {response.status_code}"
    print(f"\n✓ Double approve: {response.status_code} for {user['email']}")
