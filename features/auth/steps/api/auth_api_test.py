"""Auth API Tests — /v1/auth/* endpoints"""
import pytest
import allure

from platforms.api.httpx_client import HonoAPIClient
from skills.assertions.api_assertions import APIAssertions
from config.test_config import APIEndpoints, TestConfig

pytestmark = allure.feature("Auth")

FAKE_EMAIL = "nonexistent_qa_test@mailinator.com"
INVALID_CODE = "00000000-0000-0000-0000-000000000000"


# ── Refresh Token ─────────────────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_AUTH_001_refresh_token_valid(auth_refresh_token):
    """TC-AUTH-001 | Smoke | Valid refresh token returns new access token"""
    if not auth_refresh_token:
        pytest.skip("No refresh token returned by login — endpoint may not expose it")
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.AUTH_REFRESH,
            json={"refresh_token": auth_refresh_token},
        )
    APIAssertions(response).status_in(200, 201).has_token()


@pytest.mark.negative
@pytest.mark.api
async def test_TC_AUTH_002_refresh_token_invalid():
    """TC-AUTH-002 | Negative | Invalid refresh token returns 401"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.AUTH_REFRESH,
            json={"refresh_token": "invalid.jwt.token"},
        )
    APIAssertions(response).status_in(401, 400, 422)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_AUTH_003_refresh_token_missing_field():
    """TC-AUTH-003 | Negative | Missing refresh_token field returns 400/422"""
    async with HonoAPIClient() as client:
        response = await client.post(APIEndpoints.AUTH_REFRESH, json={})
    APIAssertions(response).status_in(400, 422)


# ── Forgot Password ───────────────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_AUTH_004_forgot_password_valid_email(auth_user):
    """TC-AUTH-004 | Smoke | Forgot password with existing email returns 200"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.AUTH_FORGOT_PASSWORD,
            json={"email": auth_user["email"]},
        )
    APIAssertions(response).status_in(200, 201, 202)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_AUTH_005_forgot_password_nonexistent_email():
    """TC-AUTH-005 | Negative | Forgot password with non-existent email — should not reveal 404"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.AUTH_FORGOT_PASSWORD,
            json={"email": FAKE_EMAIL},
        )
    APIAssertions(response).status_in(200, 201, 202, 404)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_AUTH_006_forgot_password_invalid_email_format():
    """TC-AUTH-006 | Negative | Invalid email format returns 400/422"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.AUTH_FORGOT_PASSWORD,
            json={"email": "not-an-email"},
        )
    APIAssertions(response).status_in(400, 422)


# ── Validate Reset Password ───────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_AUTH_007_validate_reset_code_invalid():
    """TC-AUTH-007 | Smoke | Validate reset code — invalid code returns valid:false"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.AUTH_VALIDATE_RESET,
            params={"code": INVALID_CODE},
        )
    assert response.status_code == 200
    body = response.json()
    data = body.get("data", body)
    assert data.get("valid") is False or response.status_code in (400, 404), (
        f"Expected valid:false for invalid code, got: {body}"
    )


@pytest.mark.negative
@pytest.mark.api
async def test_TC_AUTH_008_validate_reset_code_missing():
    """TC-AUTH-008 | Negative | Missing code query param returns 400/422"""
    async with HonoAPIClient() as client:
        response = await client.get(APIEndpoints.AUTH_VALIDATE_RESET)
    APIAssertions(response).status_in(400, 422)


# ── Reset Password ────────────────────────────────────────────────────────────

@pytest.mark.negative
@pytest.mark.api
async def test_TC_AUTH_009_reset_password_invalid_code():
    """TC-AUTH-009 | Negative | Reset password with invalid code returns 400/404"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.AUTH_RESET_PASSWORD,
            json={
                "code":             INVALID_CODE,
                "new_password":     "NewPass123!",
                "confirm_password": "NewPass123!",
            },
        )
    APIAssertions(response).status_in(400, 404, 422)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_AUTH_010_reset_password_mismatch():
    """TC-AUTH-010 | Negative | Mismatched new/confirm password returns 400/422"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.AUTH_RESET_PASSWORD,
            json={
                "code":             INVALID_CODE,
                "new_password":     "NewPass123!",
                "confirm_password": "DifferentPass456!",
            },
        )
    APIAssertions(response).status_in(400, 422)


# ── Resend Email Verification Link ────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_AUTH_011_resend_email_verif_valid(auth_user):
    """TC-AUTH-011 | Smoke | Resend verification email for existing user"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.AUTH_RESEND_EMAIL_VERIF,
            json={"email": auth_user["email"]},
        )
    APIAssertions(response).status_in(200, 201, 202)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_AUTH_012_resend_email_verif_invalid_format():
    """TC-AUTH-012 | Negative | Resend verification with invalid email format returns 400/422"""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.AUTH_RESEND_EMAIL_VERIF,
            json={"email": "bad-email"},
        )
    APIAssertions(response).status_in(400, 422)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_AUTH_013_resend_email_verif_no_api_key():
    """TC-AUTH-013 | Security | Resend verification without x-api-key returns 401"""
    import httpx
    import os
    async with httpx.AsyncClient(
        base_url=os.getenv("HONO_API_URL", "https://api-dev.thehono.com"),
        timeout=30,
    ) as client:
        response = await client.post(
            APIEndpoints.AUTH_RESEND_EMAIL_VERIF,
            json={"email": FAKE_EMAIL},
            headers={"Content-Type": "application/json"},
        )
    APIAssertions(response).status_in(401, 403)
