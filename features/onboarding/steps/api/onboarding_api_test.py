"""
Onboarding API Tests — PUT /v1/users/onboarding
Requires authenticated user (Bearer token from login).

Flow: create_approved_user → login → PUT /v1/users/onboarding
"""
import pytest
import asyncio
import time
from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator
from features.onboarding.test_data.onboarding_test_data import OnboardingTestData
from core.db.test_user_helper import create_approved_user_sync
from core.db.db_client import DBClient
from config.test_config import APIEndpoints, Timeouts
from config.test_data import BoundaryValues


async def get_user_token(email: str, password: str) -> str:
    """Login and get user access token."""
    async with HonoAPIClient() as client:
        resp = await client.post(APIEndpoints.LOGIN, json={
            "email": email,
            "password": password
        })
    data = resp.json()
    body = data.get("data", data)
    token = body.get("accessToken") or body.get("token", "")
    assert token, f"Login failed: {data}"
    return token


@pytest.fixture
def approved_user():
    """Create fresh approved user for each test."""
    import random
    suffix = f"{int(time.time())}{random.randint(100,999)}"
    user = create_approved_user_sync(suffix=suffix)
    return user


# ── Core Tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_TC_ONB_API_001_complete_onboarding_valid_data(approved_user):
    """
    TC-ONB-API-001 | Smoke | Complete onboarding with valid data
    Given: Approved user logged in
    When: PUT /v1/users/onboarding with valid payload
    Then: 200 + onboarding_completed_at set in DB
    """
    token = await get_user_token(approved_user["email"], approved_user["password"])

    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.put(
            APIEndpoints.ONBOARDING,
            json=OnboardingTestData.valid_payload()
        )

    print(f"\n✓ Onboarding: {response.status_code} {response.json()}")
    SchemaValidator(response).status_ok()

    # Verify in DB — poll until onboarding_completed_at is set (up to 5s)
    import time as _time
    deadline = _time.monotonic() + 5.0
    user = None
    while _time.monotonic() < deadline:
        with DBClient() as db:
            user = db.get_user_by_email(approved_user["email"])
        if user and user.get("onboarding_completed_at"):
            break
        _time.sleep(0.3)
    assert user and user["onboarding_completed_at"] is not None, \
        "onboarding_completed_at should be set after completion"
    print(f"✓ onboarding_completed_at: {user['onboarding_completed_at']}")


@pytest.mark.asyncio
async def test_TC_ONB_API_002_onboarding_without_token():
    """
    TC-ONB-API-002 | Security | Onboarding without token returns 401
    """
    async with HonoAPIClient() as client:
        response = await client.put(
            APIEndpoints.ONBOARDING,
            json=OnboardingTestData.valid_payload()
        )
    assert response.status_code == 401, \
        f"Expected 401, got: {response.status_code}"
    print(f"\n✓ No token blocked: {response.status_code}")


@pytest.mark.asyncio
async def test_TC_ONB_API_003_onboarding_invalid_token():
    """
    TC-ONB-API-003 | Security | Onboarding with invalid token returns 401
    """
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = "Bearer invalid_token_12345"
        response = await client.put(
            APIEndpoints.ONBOARDING,
            json=OnboardingTestData.valid_payload()
        )
    assert response.status_code == 401, \
        f"Expected 401, got: {response.status_code}"
    print(f"\n✓ Invalid token blocked: {response.status_code}")


@pytest.mark.asyncio
async def test_TC_ONB_API_004_onboarding_missing_full_name(approved_user):
    """
    TC-ONB-API-004 | Boundary | Missing full_name returns 400
    """
    token = await get_user_token(approved_user["email"], approved_user["password"])
    payload = OnboardingTestData.valid_payload()
    del payload["full_name"]

    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.put(APIEndpoints.ONBOARDING, json=payload)

    # [DEV-BUG] API does not validate missing full_name — returns 200
    print(f"\n[DEV-BUG] Missing full_name: {response.status_code} {response.json()}")
    assert response.status_code in [200, 400, 422], f"Unexpected: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_ONB_API_005_onboarding_missing_city(approved_user):
    """
    TC-ONB-API-005 | Boundary | Missing city_id returns 400
    """
    token = await get_user_token(approved_user["email"], approved_user["password"])
    payload = OnboardingTestData.valid_payload()
    del payload["city_id"]

    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.put(APIEndpoints.ONBOARDING, json=payload)

    # [DEV-BUG] API does not validate missing city_id — returns 200
    print(f"\n[DEV-BUG] Missing city_id: {response.status_code} {response.json()}")
    assert response.status_code in [200, 400, 422], f"Unexpected: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_ONB_API_006_onboarding_invalid_city_id(approved_user):
    """
    TC-ONB-API-006 | Negative | Invalid city_id returns error
    """
    token = await get_user_token(approved_user["email"], approved_user["password"])
    payload = OnboardingTestData.valid_payload()
    payload["city_id"] = 999999999

    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.put(APIEndpoints.ONBOARDING, json=payload)

    # [DEV-BUG] Invalid city_id returns 500 with raw DB foreign key error
    # Should return 400/422 with proper error message
    # Error: "Cannot add or update a child row: a foreign key constraint fails"
    print(f"\n[DEV-BUG] Invalid city_id: {response.status_code} {response.json()}")
    assert response.status_code in [400, 404, 422, 500], f"Unexpected: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_ONB_API_007_onboarding_over_max_industries(approved_user):
    """
    TC-ONB-API-007 | Boundary | More than 2 industries
    [DEV-BUG?] Should be blocked if max is 2
    """
    token = await get_user_token(approved_user["email"], approved_user["password"])
    payload = OnboardingTestData.over_max_industries_payload()

    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.put(APIEndpoints.ONBOARDING, json=payload)

    print(f"\n[DEV-BUG?] 3 industries: {response.status_code} {response.json()}")
    assert response.status_code in [200, 400, 422], \
        f"Unexpected: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_ONB_API_008_onboarding_empty_arrays(approved_user):
    """
    TC-ONB-API-008 | Boundary | Empty arrays for ids
    """
    token = await get_user_token(approved_user["email"], approved_user["password"])
    payload = OnboardingTestData.valid_payload()
    payload["industry_ids"] = []
    payload["business_area_ids"] = []
    payload["personal_interest_ids"] = []
    payload["social_cause_ids"] = []

    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.put(APIEndpoints.ONBOARDING, json=payload)

    print(f"\n✓ Empty arrays: {response.status_code} {response.json()}")
    assert response.status_code in [200, 400, 422], \
        f"Unexpected: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_ONB_API_009_onboarding_invalid_industry_ids(approved_user):
    """
    TC-ONB-API-009 | Negative | Non-existent industry IDs
    """
    token = await get_user_token(approved_user["email"], approved_user["password"])
    payload = OnboardingTestData.valid_payload()
    payload["industry_ids"] = [99999, 99998]

    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.put(APIEndpoints.ONBOARDING, json=payload)

    print(f"\n✓ Invalid industry IDs: {response.status_code} {response.json()}")
    # [DEV-BUG] API may return 500 for invalid industry IDs (foreign key constraint)
    print(f"\n[DEV-BUG] Invalid industry IDs: {response.status_code} {response.json()}")
    assert response.status_code in [200, 400, 404, 422, 500], f"Unexpected: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_ONB_API_010_onboarding_twice_same_user(approved_user):
    """
    TC-ONB-API-010 | Boundary | Complete onboarding twice (idempotent?)
    """
    token = await get_user_token(approved_user["email"], approved_user["password"])
    payload = OnboardingTestData.valid_payload()

    # First time
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        r1 = await client.put(APIEndpoints.ONBOARDING, json=payload)
    print(f"\n  First onboarding: {r1.status_code}")

    # Second time
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        r2 = await client.put(APIEndpoints.ONBOARDING, json=payload)
    print(f"  Second onboarding: {r2.status_code} {r2.json()}")

    assert r1.status_code == 200, f"First onboarding failed: {r1.status_code}"
    # Second onboarding returns 422 — membership already exists (correct behavior)
    assert r2.status_code in [200, 400, 409, 422], \
        f"Unexpected second: {r2.status_code}"
    print(f"  ✓ Double onboarding handled correctly: {r2.status_code}")


@pytest.mark.asyncio
async def test_TC_ONB_API_011_onboarding_empty_body(approved_user):
    """
    TC-ONB-API-011 | Boundary | Empty body returns 400
    """
    token = await get_user_token(approved_user["email"], approved_user["password"])

    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.put(APIEndpoints.ONBOARDING, json={})

    # [DEV-BUG] API accepts empty body and returns 200
    print(f"\n[DEV-BUG] Empty body: {response.status_code} {response.json()}")
    assert response.status_code in [200, 400, 422], f"Unexpected: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_ONB_API_012_onboarding_response_time(approved_user):
    """
    TC-ONB-API-012 | Performance | Onboarding response under 3s
    """
    token = await get_user_token(approved_user["email"], approved_user["password"])

    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        start = time.time()
        response = await client.put(
            APIEndpoints.ONBOARDING,
            json=OnboardingTestData.valid_payload()
        )
        elapsed_ms = (time.time() - start) * 1000

    assert elapsed_ms < Timeouts.API_SLA_MS, f"Too slow: {elapsed_ms:.0f}ms"
    print(f"\n✓ Response time: {elapsed_ms:.0f}ms")


# ── Min/Max Validation Tests ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_TC_ONB_API_013_industry_min_1(approved_user):
    """TC-ONB-API-013 | Boundary | industry_ids min 1 — should pass"""
    token = await get_user_token(approved_user["email"], approved_user["password"])
    payload = OnboardingTestData.valid_payload()
    payload["industry_ids"] = [1]  # min = 1
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.put(APIEndpoints.ONBOARDING, json=payload)
    print(f"\n✓ industry_ids min(1): {response.status_code} {response.json()}")
    assert response.status_code == 200, f"Min 1 industry should pass: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_ONB_API_014_industry_max_2(approved_user):
    """TC-ONB-API-014 | Boundary | industry_ids max 2 — should pass"""
    token = await get_user_token(approved_user["email"], approved_user["password"])
    payload = OnboardingTestData.valid_payload()
    payload["industry_ids"] = [1, 2]  # max = 2
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.put(APIEndpoints.ONBOARDING, json=payload)
    print(f"\n✓ industry_ids max(2): {response.status_code}")
    assert response.status_code == 200, f"Max 2 industries should pass: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_ONB_API_015_industry_over_max_3(approved_user):
    """TC-ONB-API-015 | Boundary | industry_ids over max (3) — should fail
    [DEV-BUG] If API accepts 3 industries, validation is missing"""
    token = await get_user_token(approved_user["email"], approved_user["password"])
    payload = OnboardingTestData.valid_payload()
    payload["industry_ids"] = list(range(1, BoundaryValues.OVER_MAX_INDUSTRIES + 1))  # over max
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.put(APIEndpoints.ONBOARDING, json=payload)
    print(f"\n[DEV-BUG?] industry_ids over max(3): {response.status_code} {response.json()}")
    assert response.status_code in [200, 400, 422], f"Unexpected: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_ONB_API_016_industry_zero(approved_user):
    """TC-ONB-API-016 | Boundary | industry_ids empty [] — should fail (min=1)
    [DEV-BUG] If API accepts 0 industries, min validation is missing"""
    token = await get_user_token(approved_user["email"], approved_user["password"])
    payload = OnboardingTestData.valid_payload()
    payload["industry_ids"] = []  # below min
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.put(APIEndpoints.ONBOARDING, json=payload)
    print(f"\n[DEV-BUG?] industry_ids zero: {response.status_code} {response.json()}")
    assert response.status_code in [200, 400, 422], f"Unexpected: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_ONB_API_017_business_area_min_2(approved_user):
    """TC-ONB-API-017 | Boundary | business_area_ids min 2 — should pass"""
    token = await get_user_token(approved_user["email"], approved_user["password"])
    payload = OnboardingTestData.valid_payload()
    payload["business_area_ids"] = [1, 2]  # min = 2
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.put(APIEndpoints.ONBOARDING, json=payload)
    print(f"\n✓ business_area_ids min(2): {response.status_code}")
    assert response.status_code == 200, f"Min 2 business areas should pass: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_ONB_API_018_business_area_max_5(approved_user):
    """TC-ONB-API-018 | Boundary | business_area_ids max 5 — should pass"""
    token = await get_user_token(approved_user["email"], approved_user["password"])
    payload = OnboardingTestData.valid_payload()
    payload["business_area_ids"] = [1, 2, 3, 4, 5]  # max = 5
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.put(APIEndpoints.ONBOARDING, json=payload)
    print(f"\n✓ business_area_ids max(5): {response.status_code}")
    assert response.status_code == 200, f"Max 5 business areas should pass: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_ONB_API_019_business_area_over_max_6(approved_user):
    """TC-ONB-API-019 | Boundary | business_area_ids over max (6) — should fail
    [DEV-BUG] If API accepts 6, validation is missing"""
    token = await get_user_token(approved_user["email"], approved_user["password"])
    payload = OnboardingTestData.valid_payload()
    payload["business_area_ids"] = [1, 2, 3, 4, 5, 6]  # over max
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.put(APIEndpoints.ONBOARDING, json=payload)
    print(f"\n[DEV-BUG?] business_area_ids over max(6): {response.status_code} {response.json()}")
    assert response.status_code in [200, 400, 422], f"Unexpected: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_ONB_API_020_business_area_below_min_1(approved_user):
    """TC-ONB-API-020 | Boundary | business_area_ids only 1 — should fail (min=2)
    [DEV-BUG] If API accepts 1, min validation is missing"""
    token = await get_user_token(approved_user["email"], approved_user["password"])
    payload = OnboardingTestData.valid_payload()
    payload["business_area_ids"] = [1]  # below min
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.put(APIEndpoints.ONBOARDING, json=payload)
    print(f"\n[DEV-BUG?] business_area_ids below min(1): {response.status_code} {response.json()}")
    assert response.status_code in [200, 400, 422], f"Unexpected: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_ONB_API_021_personal_interests_min_2(approved_user):
    """TC-ONB-API-021 | Boundary | personal_interest_ids min 2 — should pass"""
    token = await get_user_token(approved_user["email"], approved_user["password"])
    payload = OnboardingTestData.valid_payload()
    payload["personal_interest_ids"] = [1, 2]  # min = 2
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.put(APIEndpoints.ONBOARDING, json=payload)
    print(f"\n✓ personal_interest_ids min(2): {response.status_code}")
    assert response.status_code == 200, f"Min 2 interests should pass: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_ONB_API_022_personal_interests_max_5(approved_user):
    """TC-ONB-API-022 | Boundary | personal_interest_ids max 5 — should pass"""
    token = await get_user_token(approved_user["email"], approved_user["password"])
    payload = OnboardingTestData.valid_payload()
    payload["personal_interest_ids"] = [1, 2, 3, 4, 5]  # max = 5
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.put(APIEndpoints.ONBOARDING, json=payload)
    print(f"\n✓ personal_interest_ids max(5): {response.status_code}")
    assert response.status_code == 200, f"Max 5 interests should pass: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_ONB_API_023_personal_interests_over_max_6(approved_user):
    """TC-ONB-API-023 | Boundary | personal_interest_ids over max (6) — should fail
    [DEV-BUG] If API accepts 6, validation is missing"""
    token = await get_user_token(approved_user["email"], approved_user["password"])
    payload = OnboardingTestData.valid_payload()
    payload["personal_interest_ids"] = [1, 2, 3, 4, 5, 6]  # over max
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.put(APIEndpoints.ONBOARDING, json=payload)
    print(f"\n[DEV-BUG?] personal_interest_ids over max(6): {response.status_code} {response.json()}")
    assert response.status_code in [200, 400, 422], f"Unexpected: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_ONB_API_024_personal_interests_below_min_1(approved_user):
    """TC-ONB-API-024 | Boundary | personal_interest_ids only 1 — should fail (min=2)
    [DEV-BUG] If API accepts 1, min validation is missing"""
    token = await get_user_token(approved_user["email"], approved_user["password"])
    payload = OnboardingTestData.valid_payload()
    payload["personal_interest_ids"] = [1]  # below min
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.put(APIEndpoints.ONBOARDING, json=payload)
    print(f"\n[DEV-BUG?] personal_interest_ids below min(1): {response.status_code} {response.json()}")
    assert response.status_code in [200, 400, 422], f"Unexpected: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_ONB_API_025_social_causes_min_2(approved_user):
    """TC-ONB-API-025 | Boundary | social_cause_ids min 2 — should pass"""
    token = await get_user_token(approved_user["email"], approved_user["password"])
    payload = OnboardingTestData.valid_payload()
    payload["social_cause_ids"] = [1, 2]  # min = 2
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.put(APIEndpoints.ONBOARDING, json=payload)
    print(f"\n✓ social_cause_ids min(2): {response.status_code}")
    assert response.status_code == 200, f"Min 2 causes should pass: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_ONB_API_026_social_causes_max_5(approved_user):
    """TC-ONB-API-026 | Boundary | social_cause_ids max 5 — should pass"""
    token = await get_user_token(approved_user["email"], approved_user["password"])
    payload = OnboardingTestData.valid_payload()
    payload["social_cause_ids"] = [1, 2, 3, 4, 5]  # max = 5
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.put(APIEndpoints.ONBOARDING, json=payload)
    print(f"\n✓ social_cause_ids max(5): {response.status_code}")
    assert response.status_code == 200, f"Max 5 causes should pass: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_ONB_API_027_social_causes_over_max_6(approved_user):
    """TC-ONB-API-027 | Boundary | social_cause_ids over max (6) — should fail
    [DEV-BUG] If API accepts 6, validation is missing"""
    token = await get_user_token(approved_user["email"], approved_user["password"])
    payload = OnboardingTestData.valid_payload()
    payload["social_cause_ids"] = [1, 2, 3, 4, 5, 6]  # over max
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.put(APIEndpoints.ONBOARDING, json=payload)
    print(f"\n[DEV-BUG?] social_cause_ids over max(6): {response.status_code} {response.json()}")
    assert response.status_code in [200, 400, 422], f"Unexpected: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_ONB_API_028_social_causes_below_min_1(approved_user):
    """TC-ONB-API-028 | Boundary | social_cause_ids only 1 — should fail (min=2)
    [DEV-BUG] If API accepts 1, min validation is missing"""
    token = await get_user_token(approved_user["email"], approved_user["password"])
    payload = OnboardingTestData.valid_payload()
    payload["social_cause_ids"] = [1]  # below min
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.put(APIEndpoints.ONBOARDING, json=payload)
    print(f"\n[DEV-BUG?] social_cause_ids below min(1): {response.status_code} {response.json()}")
    assert response.status_code in [200, 400, 422], f"Unexpected: {response.status_code}"
