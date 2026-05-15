"""User password API tests — PUT /v1/users/me/password."""

import pytest
import pytest_asyncio

from core.db.test_user_helper import create_approved_user
from features.users_password.test_data.users_password_test_data import (
    UsersPasswordTestData,
)
from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator

CHANGE_PASSWORD_PATH = "/v1/users/me/password"


async def login_status(email: str, password: str) -> int:
    async with HonoAPIClient() as client:
        response = await client.post(
            "/v1/users/login",
            json={"email": email, "password": password},
        )
    return response.status_code


@pytest_asyncio.fixture(scope="function")
async def approved_password_user() -> dict:
    return await create_approved_user(
        fullname="Password API Test User",
        password=UsersPasswordTestData.CURRENT_PASSWORD,
    )


@pytest_asyncio.fixture(scope="function")
async def auth_client(approved_password_user):
    async with HonoAPIClient() as client:
        await client.login(
            approved_password_user["email"],
            approved_password_user["password"],
        )
        yield client


@pytest.mark.asyncio
async def test_TC_USERS_PASSWORD_001_change_password_success(
    approved_password_user,
    auth_client,
):
    """
    TC-USERS-PASSWORD-001 | Smoke/Security
    Given an approved synthetic user is authenticated
    When PUT /v1/users/me/password with current_password and new_password
    Then the password is changed and old credentials no longer work
    """
    response = await auth_client.put(
        CHANGE_PASSWORD_PATH,
        json=UsersPasswordTestData.valid_change_payload(),
    )

    SchemaValidator(response).status_ok().response_time_under(3000)

    old_login_status = await login_status(
        approved_password_user["email"],
        UsersPasswordTestData.CURRENT_PASSWORD,
    )
    assert old_login_status == 401, (
        "Old password should be rejected after successful password change."
    )

    new_login_status = await login_status(
        approved_password_user["email"],
        UsersPasswordTestData.NEW_PASSWORD,
    )
    assert new_login_status == 200, (
        "New password should authenticate after successful password change."
    )


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
    When current_password is wrong
    Then the request is rejected and the original password still works
    """
    response = await auth_client.put(
        CHANGE_PASSWORD_PATH,
        json=UsersPasswordTestData.wrong_current_payload(),
    )

    assert response.status_code in [400, 401, 422], (
        f"Expected password validation rejection, got {response.status_code}: "
        f"{response.text[:200]}"
    )

    current_login_status = await login_status(
        approved_password_user["email"],
        UsersPasswordTestData.CURRENT_PASSWORD,
    )
    assert current_login_status == 200, (
        "Original password should still work after rejected password change."
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field_name", "payload"),
    [
        (
            "current_password",
            UsersPasswordTestData.missing_current_password_payload(),
        ),
        (
            "new_password",
            UsersPasswordTestData.missing_new_password_payload(),
        ),
    ],
)
async def test_TC_USERS_PASSWORD_004_missing_required_field(
    auth_client,
    field_name,
    payload,
):
    """
    TC-USERS-PASSWORD-004 | Boundary/Negative
    Given an authenticated synthetic user
    When a required password field is missing
    Then the API returns a validation error
    """
    response = await auth_client.put(CHANGE_PASSWORD_PATH, json=payload)

    assert response.status_code in [400, 422], (
        f"Expected validation error for missing {field_name}, got "
        f"{response.status_code}: {response.text[:200]}"
    )
