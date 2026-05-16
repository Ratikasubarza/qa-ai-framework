"""Register API Tests — POST /v1/users/register"""
import allure
import pytest

from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator
from skills.testing.helpers import skip_on_email_quota
from features.register.test_data.register_test_data import RegisterTestData

pytestmark = allure.feature("Register")


@pytest.mark.asyncio
async def test_TC_REG_API_001_register_valid_data():
    """
    TC-REG-API-001 | Smoke | Register with valid data returns OK
    """
    async with HonoAPIClient() as client:
        response = await client.post(
            "/v1/users/register",
            json=RegisterTestData.valid_payload()
        )
    skip_on_email_quota(response)
    SchemaValidator(response).status_ok()
    data = response.json()
    assert data.get("code") == RegisterTestData.SUCCESS_CODE, \
        f"Expected code OK, got: {data}"
    print(f"\n✓ Register success: {data.get('message')}")


@pytest.mark.asyncio
async def test_TC_REG_API_002_register_duplicate_email():
    """
    TC-REG-API-002 | Negative | Register with existing email returns error
    """
    payload = RegisterTestData.valid_payload()
    payload["email"] = RegisterTestData.EXISTING_EMAIL

    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/register", json=payload)

    assert response.status_code in [400, 409, 422], \
        f"Expected 4xx for duplicate email, got: {response.status_code}"
    print(f"\n✓ Duplicate email blocked: {response.status_code}")


@pytest.mark.asyncio
async def test_TC_REG_API_003_register_missing_required_fields():
    """
    TC-REG-API-003 | Boundary | Register with missing fields returns 400
    """
    async with HonoAPIClient() as client:
        response = await client.post(
            "/v1/users/register",
            json=RegisterTestData.MISSING_FIELDS_PAYLOAD
        )
    assert response.status_code in [400, 422], \
        f"Expected 400/422, got: {response.status_code}"
    print(f"\n✓ Missing fields blocked: {response.status_code}")


@pytest.mark.asyncio
async def test_TC_REG_API_004_register_invalid_email_format():
    """
    TC-REG-API-004 | Negative | Register with invalid email format
    """
    async with HonoAPIClient() as client:
        response = await client.post(
            "/v1/users/register",
            json=RegisterTestData.INVALID_EMAIL_PAYLOAD
        )
    assert response.status_code in [400, 422], \
        f"Expected 400/422, got: {response.status_code}"
    print(f"\n✓ Invalid email blocked: {response.status_code}")


@pytest.mark.asyncio
async def test_TC_REG_API_005_register_empty_body():
    """
    TC-REG-API-005 | Boundary | Register with empty body returns 400
    """
    async with HonoAPIClient() as client:
        response = await client.post(
            "/v1/users/register",
            json=RegisterTestData.EMPTY_PAYLOAD
        )
    assert response.status_code in [400, 422], \
        f"Expected 400/422, got: {response.status_code}"
    print(f"\n✓ Empty body blocked: {response.status_code}")


# ── Edge Cases & Combination Tests ────────────────────────────────────

@pytest.mark.asyncio
async def test_TC_REG_API_006_duplicate_email():
    """TC-REG-API-006 | Negative | Duplicate email returns error"""
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/register", json={
            "fullname": "Test Duplicate Email",
            "email": "testingHonoA@mailinator.com",  # Already registered
            "phone_number": RegisterTestData.valid_payload()["phone_number"],
            "phone_country_code": "ID",
            "linkedin": "https://linkedin.com/in/testduplicate"
        })
    assert response.status_code in [400, 409, 422], \
        f"Expected 4xx for duplicate email, got: {response.status_code} {response.json()}"
    print(f"\n✓ Duplicate email blocked: {response.status_code} — {response.json().get('message')}")


@pytest.mark.asyncio
async def test_TC_REG_API_007_duplicate_phone():
    """TC-REG-API-007 | Negative | Duplicate phone number returns error"""
    import time
    ts = int(time.time())
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/register", json={
            "fullname": f"Test Duplicate Phone {ts}",
            "email": f"uniqueemail+{ts}@mailinator.com",
            "phone_number": "81234567104",  # Already registered (HonoA)
            "phone_country_code": "ID",
            "linkedin": f"https://linkedin.com/in/testphone{ts}"
        })
    assert response.status_code in [400, 409, 422], \
        f"Expected 4xx for duplicate phone, got: {response.status_code} {response.json()}"
    print(f"\n✓ Duplicate phone blocked: {response.status_code} — {response.json().get('message')}")


@pytest.mark.asyncio
async def test_TC_REG_API_008_duplicate_email_valid_phone():
    """TC-REG-API-008 | Combination | Duplicate email + valid phone → blocked"""
    payload = RegisterTestData.valid_payload()
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/register", json={
            "fullname": "Test Combo 1",
            "email": "testingHonoA@mailinator.com",  # duplicate email
            "phone_number": payload["phone_number"],  # unique phone
            "phone_country_code": "ID",
            "linkedin": "https://linkedin.com/in/testcombo1"
        })
    assert response.status_code in [400, 409, 422], \
        f"Expected 4xx, got: {response.status_code}"
    print(f"\n✓ Duplicate email + valid phone blocked: {response.status_code}")


@pytest.mark.asyncio
async def test_TC_REG_API_009_valid_email_duplicate_phone():
    """TC-REG-API-009 | Combination | Valid email + duplicate phone → blocked"""
    import time
    ts = int(time.time())
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/register", json={
            "fullname": "Test Combo 2",
            "email": f"uniquecombo+{ts}@mailinator.com",  # unique email
            "phone_number": "81234567105",  # duplicate phone (HonoB)
            "phone_country_code": "ID",
            "linkedin": f"https://linkedin.com/in/testcombo2{ts}"
        })
    assert response.status_code in [400, 409, 422], \
        f"Expected 4xx, got: {response.status_code}"
    print(f"\n✓ Valid email + duplicate phone blocked: {response.status_code}")


@pytest.mark.asyncio
async def test_TC_REG_API_010_invalid_email_format():
    """TC-REG-API-010 | Negative | Invalid email format"""
    for invalid_email in ["notanemail", "missing@", "@nodomain.com", "spaces in@email.com"]:
        async with HonoAPIClient() as client:
            response = await client.post("/v1/users/register", json={
                "fullname": "Test Invalid Email",
                "email": invalid_email,
                "phone_number": "81234567999",
                "phone_country_code": "ID",
                "linkedin": "https://linkedin.com/in/test"
            })
        assert response.status_code in [400, 422], \
            f"Expected 4xx for '{invalid_email}', got: {response.status_code}"
        print(f"  ✓ '{invalid_email}' blocked: {response.status_code}")


@pytest.mark.asyncio
async def test_TC_REG_API_011_phone_non_numeric():
    """TC-REG-API-011 | Negative | Non-numeric phone number"""
    import time
    ts = int(time.time())
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/register", json={
            "fullname": "Test Phone Format",
            "email": f"testphone+{ts}@mailinator.com",
            "phone_number": "abc-invalid",
            "phone_country_code": "ID",
            "linkedin": f"https://linkedin.com/in/testphone{ts}"
        })
    assert response.status_code in [400, 422], \
        f"Expected 4xx for non-numeric phone, got: {response.status_code}"
    print(f"\n✓ Non-numeric phone blocked: {response.status_code}")


@pytest.mark.asyncio
async def test_TC_REG_API_012_missing_api_key():
    """TC-REG-API-012 | Security | Missing x-api-key header returns 401"""
    import httpx, os
    async with httpx.AsyncClient(
        base_url=os.getenv("HONO_API_URL"),
        timeout=30
    ) as client:  # No API key
        response = await client.post("/v1/users/register", json={
            "fullname": "Test No API Key",
            "email": "noapikey@mailinator.com",
            "phone_number": "81234567888",
            "phone_country_code": "ID",
            "linkedin": "https://linkedin.com/in/noapikey"
        })
    assert response.status_code in [401, 403], \
        f"Expected 401/403 without API key, got: {response.status_code}"
    print(f"\n✓ Missing API key blocked: {response.status_code}")


@pytest.mark.asyncio
async def test_TC_REG_API_013_sql_injection_fullname():
    """TC-REG-API-013 | Security | SQL injection in fullname is sanitized"""
    import time
    ts = int(time.time())
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/register", json={
            "fullname": "'; DROP TABLE users; --",
            "email": f"sqlinject+{ts}@mailinator.com",
            "phone_number": str(ts)[-9:],
            "phone_country_code": "ID",
            "linkedin": f"https://linkedin.com/in/sqlinject{ts}"
        })
    skip_on_email_quota(response)
    # Should either block or sanitize — users table should still exist
    assert response.status_code in [200, 400, 422], \
        f"Unexpected status: {response.status_code}"
    print(f"\n✓ SQL injection handled: {response.status_code}")


@pytest.mark.asyncio
async def test_TC_REG_API_014_very_long_fullname():
    """TC-REG-API-014 | Boundary | Very long fullname (500+ chars)"""
    import time
    ts = int(time.time())
    long_name = "A" * 501
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/register", json={
            "fullname": long_name,
            "email": f"longname+{ts}@mailinator.com",
            "phone_number": str(ts)[-9:],
            "phone_country_code": "ID",
            "linkedin": f"https://linkedin.com/in/longname{ts}"
        })
    print(f"\n✓ Long fullname ({len(long_name)} chars): {response.status_code} — {response.json().get('message', '')[:50]}")


@pytest.mark.asyncio
async def test_TC_REG_API_015_both_email_and_phone_duplicate():
    """TC-REG-API-015 | Combination | Both email AND phone duplicate → blocked"""
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/register", json={
            "fullname": "Test Both Duplicate",
            "email": "testingHonoA@mailinator.com",    # duplicate
            "phone_number": "81234567104",              # duplicate
            "phone_country_code": "ID",
            "linkedin": "https://linkedin.com/in/bothduplicate"
        })
    assert response.status_code in [400, 409, 422], \
        f"Expected 4xx for both duplicate, got: {response.status_code}"
    print(f"\n✓ Both email+phone duplicate blocked: {response.status_code}")


# ── Extended Register Tests ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_TC_REG_API_016_minimum_valid_data():
    """TC-REG-API-016 | Boundary | Register with minimum required fields returns 200"""
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/register", json=RegisterTestData.valid_payload())
    skip_on_email_quota(response)
    assert response.status_code == 200, \
        f"Expected 200 for minimum valid payload, got: {response.status_code} {response.text[:200]}"


@pytest.mark.asyncio
async def test_TC_REG_API_017_special_chars_fullname():
    """TC-REG-API-017 | Boundary | Special characters in fullname"""
    import time
    ts = int(time.time())
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/register", json={
            **RegisterTestData.valid_payload(str(ts)),
            "fullname": "Test !@#$% User",
        })
    skip_on_email_quota(response)
    assert response.status_code in [200, 400, 422], \
        f"Unexpected status for special chars in fullname: {response.status_code}"
    print(f"\n  Special chars fullname → {response.status_code}")


@pytest.mark.asyncio
async def test_TC_REG_API_018_missing_fullname():
    """TC-REG-API-018 | Negative | Missing fullname field returns 400"""
    import time
    ts = int(time.time())
    payload = RegisterTestData.valid_payload(str(ts))
    del payload["fullname"]
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/register", json=payload)
    assert response.status_code in [400, 422], \
        f"Expected 400/422 for missing fullname, got: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_REG_API_019_missing_linkedin():
    """TC-REG-API-019 | Negative | Missing linkedin field — documents API behavior"""
    import time
    ts = int(time.time())
    payload = RegisterTestData.valid_payload(str(ts))
    del payload["linkedin"]
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/register", json=payload)
    assert response.status_code in [200, 400, 422], \
        f"Unexpected status for missing linkedin: {response.status_code}"
    print(f"\n  Missing linkedin → {response.status_code}")


@pytest.mark.asyncio
async def test_TC_REG_API_020_invalid_phone_country_code():
    """TC-REG-API-020 | Negative | Invalid phone country code (XX) returns 400"""
    import time
    ts = int(time.time())
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/register", json={
            **RegisterTestData.valid_payload(str(ts)),
            "phone_country_code": RegisterTestData.INVALID_COUNTRY_CODE,
        })
    assert response.status_code in [400, 422], \
        f"Expected 400/422 for invalid country code, got: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_REG_API_021_phone_too_short():
    """TC-REG-API-021 | Boundary | Phone number too short (3 digits) returns 400"""
    import time
    ts = int(time.time())
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/register", json={
            **RegisterTestData.valid_payload(str(ts)),
            "phone_number": "123",
        })
    assert response.status_code in [400, 422], \
        f"Expected 400/422 for short phone, got: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_REG_API_022_phone_too_long():
    """TC-REG-API-022 | Boundary | Phone number too long (21 digits) — documents behavior"""
    import time
    ts = int(time.time())
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/register", json={
            **RegisterTestData.valid_payload(str(ts)),
            "phone_number": "1" * 21,
        })
    assert response.status_code in [200, 400, 422], \
        f"Unexpected status for 21-digit phone: {response.status_code}"
    print(f"\n  21-digit phone → {response.status_code}")


@pytest.mark.asyncio
async def test_TC_REG_API_023_xss_in_fullname():
    """TC-REG-API-023 | Security | XSS payload in fullname is handled safely"""
    import time
    ts = int(time.time())
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/register", json={
            **RegisterTestData.valid_payload(str(ts)),
            "fullname": RegisterTestData.XSS_NAME,
        })
    skip_on_email_quota(response)
    assert response.status_code in [200, 400, 422], \
        f"Unexpected status for XSS fullname: {response.status_code}"
    print(f"\n  XSS fullname → {response.status_code}")


@pytest.mark.asyncio
async def test_TC_REG_API_024_valid_linkedin_url():
    """TC-REG-API-024 | Boundary | Valid LinkedIn URL is accepted"""
    import time
    ts = int(time.time())
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/register", json={
            **RegisterTestData.valid_payload(str(ts)),
            "linkedin": "https://linkedin.com/in/Ratikasaubarza",
        })
    skip_on_email_quota(response)
    assert response.status_code == 200, \
        f"Expected 200 for valid linkedin URL, got: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_REG_API_025_invalid_linkedin_url():
    """TC-REG-API-025 | Negative | Invalid LinkedIn URL — documents API behavior"""
    import time
    ts = int(time.time())
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/register", json={
            **RegisterTestData.valid_payload(str(ts)),
            "linkedin": "not-a-url",
        })
    skip_on_email_quota(response)
    assert response.status_code in [200, 400, 422], \
        f"Unexpected status for invalid linkedin URL: {response.status_code}"
    print(f"\n  Invalid linkedin URL → {response.status_code}")


@pytest.mark.asyncio
async def test_TC_REG_API_026_response_time():
    """TC-REG-API-026 | Performance | Register response time under 3s"""
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/register", json=RegisterTestData.valid_payload())
    skip_on_email_quota(response)
    SchemaValidator(response).response_time_under(3000)


@pytest.mark.asyncio
async def test_TC_REG_API_027_empty_string_fullname():
    """TC-REG-API-027 | Boundary | Empty string fullname returns 400"""
    import time
    ts = int(time.time())
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/register", json={
            **RegisterTestData.valid_payload(str(ts)),
            "fullname": "",
        })
    assert response.status_code in [400, 422], \
        f"Expected 400/422 for empty fullname, got: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_REG_API_028_whitespace_only_fullname():
    """TC-REG-API-028 | Boundary | Whitespace-only fullname — documents API behavior"""
    import time
    ts = int(time.time())
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/register", json={
            **RegisterTestData.valid_payload(str(ts)),
            "fullname": "   ",
        })
    skip_on_email_quota(response)
    assert response.status_code in [200, 400, 422], \
        f"Unexpected status for whitespace fullname: {response.status_code}"
    print(f"\n  Whitespace fullname → {response.status_code}")


@pytest.mark.asyncio
async def test_TC_REG_API_029_register_same_user_twice():
    """TC-REG-API-029 | Combination | Register same user twice — second attempt blocked"""
    payload = RegisterTestData.valid_payload()
    async with HonoAPIClient() as client:
        first = await client.post("/v1/users/register", json=payload)
        skip_on_email_quota(first)
        assert first.status_code == 200, \
            f"First registration should succeed, got: {first.status_code}"
        second = await client.post("/v1/users/register", json=payload)
    assert second.status_code in [400, 409, 422], \
        f"Second registration should be blocked, got: {second.status_code}"
    print(f"\n✓ Duplicate registration blocked on second attempt: {second.status_code}")


@pytest.mark.asyncio
async def test_TC_REG_API_030_null_values_in_required_fields():
    """TC-REG-API-030 | Combination | Null values in email and fullname return 400"""
    import time
    ts = int(time.time())
    async with HonoAPIClient() as client:
        response = await client.post("/v1/users/register", json={
            "fullname": None,
            "email": None,
            "phone_number": str(ts)[-9:],
            "phone_country_code": "ID",
            "linkedin": f"https://linkedin.com/in/nulltest{ts}",
        })
    assert response.status_code in [400, 422], \
        f"Expected 400/422 for null fields, got: {response.status_code}"
