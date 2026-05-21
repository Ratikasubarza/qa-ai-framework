"""User password API tests — PUT /v1/users/me/password."""
import allure
import pytest
import pytest_asyncio

from core.db.test_user_helper import create_approved_user
from features.users_password.test_data.users_password_test_data import (
    UsersPasswordTestData,
)
from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator
from skills.testing.helpers import skip_on_email_quota
from config.test_config import APIEndpoints

CHANGE_PASSWORD_PATH = APIEndpoints.ME_PASSWORD

pytestmark = allure.feature("Users - Password")


# ── Helpers ───────────────────────────────────────────────────────────────────

async def login_status(email: str, password: str) -> int:
    """Return the HTTP status code of a login attempt."""
    async with HonoAPIClient() as client:
        response = await client.post(
            APIEndpoints.LOGIN,
            json={"email": email, "password": password},
        )
    return response.status_code


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def approved_password_user() -> dict:
    """
    Create a fully approved synthetic user whose password is exactly
    UsersPasswordTestData.CURRENT_PASSWORD — guaranteed via DB override.

    Using set_known_password() means this fixture stays correct even if
    the approval flow generates a different temporary password.
    """
    user = await create_approved_user(
        fullname="Password API Test User",
        password=UsersPasswordTestData.CURRENT_PASSWORD,
    )
    # Guarantee DB is in sync with the constant (double-write is idempotent)
    UsersPasswordTestData.set_known_password(user["email"])
    return user


@pytest_asyncio.fixture(scope="function")
async def auth_client(approved_password_user):
    """Authenticated client using the fixture user's known current password."""
    async with HonoAPIClient() as client:
        await client.login(
            approved_password_user["email"],
            UsersPasswordTestData.CURRENT_PASSWORD,
        )
        yield client


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_TC_USERS_PASSWORD_001_change_password_success(
    approved_password_user,
    auth_client,
):
    """
    TC-USERS-PASSWORD-001 | Smoke/Security
    Given an approved synthetic user is authenticated
    When PUT /v1/users/me/password with current_password and new_password
    Then the password is changed: old credentials rejected, new credentials accepted
    After: DB reset to CURRENT_PASSWORD so user stays reusable
    """
    response = await auth_client.put(
        CHANGE_PASSWORD_PATH,
        json=UsersPasswordTestData.valid_change_payload(),
    )
    skip_on_email_quota(response)
    SchemaValidator(response).status_ok().response_time_under(3000)

    old_status = await login_status(
        approved_password_user["email"],
        UsersPasswordTestData.CURRENT_PASSWORD,
    )
    assert old_status == 401, (
        "Old password should be rejected after successful password change."
    )

    new_status = await login_status(
        approved_password_user["email"],
        UsersPasswordTestData.NEW_PASSWORD,
    )
    assert new_status == 200, (
        "New password should authenticate after successful password change."
    )

    # Reset DB so the user record is clean regardless of test order
    UsersPasswordTestData.reset_password(approved_password_user["email"])


@pytest.mark.asyncio
async def test_TC_USERS_PASSWORD_002_change_password_without_token():
    """
    TC-USERS-PASSWORD-002 | Security
    Given no bearer token is provided
    When PUT /v1/users/me/password
    Then the API returns 401
    """
    async with HonoAPIClient() as client:
        response = await client.put(
            CHANGE_PASSWORD_PATH,
            json=UsersPasswordTestData.valid_change_payload(),
        )
    SchemaValidator(response).status_unauthorized()


@pytest.mark.asyncio
async def test_TC_USERS_PASSWORD_003_wrong_current_password_preserves_password(
    approved_password_user,
    auth_client,
):
    """
    TC-USERS-PASSWORD-003 | Negative
    Given an authenticated synthetic user
    When current_password field contains the wrong value
    Then the request is rejected and the original password still works
    """
    response = await auth_client.put(
        CHANGE_PASSWORD_PATH,
        json=UsersPasswordTestData.wrong_current_payload(),
    )
    skip_on_email_quota(response)
    assert response.status_code in [400, 401, 422], (
        f"Expected password validation rejection, got {response.status_code}: "
        f"{response.text[:200]}"
    )

    current_status = await login_status(
        approved_password_user["email"],
        UsersPasswordTestData.CURRENT_PASSWORD,
    )
    assert current_status == 200, (
        "Original password should still work after a rejected password change."
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("missing_field", "payload"),
    [
        ("current_password", UsersPasswordTestData.missing_current_password_payload()),
        ("new_password",     UsersPasswordTestData.missing_new_password_payload()),
    ],
    ids=["missing_current_password", "missing_new_password"],
)
async def test_TC_USERS_PASSWORD_004_missing_required_field(
    auth_client,
    missing_field,
    payload,
):
    """
    TC-USERS-PASSWORD-004 | Boundary/Negative
    Given an authenticated synthetic user
    When a required password field is absent from the request body
    Then the API returns a validation error (400 or 422)
    """
    response = await auth_client.put(CHANGE_PASSWORD_PATH, json=payload)
    skip_on_email_quota(response)
    assert response.status_code in [400, 422], (
        f"Expected validation error for missing '{missing_field}', "
        f"got {response.status_code}: {response.text[:200]}"
    )
