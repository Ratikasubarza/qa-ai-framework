"""User email API tests — PUT /v1/users/me/email."""

import pytest
import pytest_asyncio

from core.db.test_user_helper import create_approved_user
from core.db.db_client import DBClient
from features.users_email.test_data.users_email_test_data import UsersEmailTestData
from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator


def assert_required_keys(payload: dict, required_keys: set[str], label: str) -> None:
    missing = required_keys - set(payload.keys())
    assert not missing, f"Missing {label} field(s): {sorted(missing)}"


def response_body(response) -> dict:
    body = response.json()
    assert isinstance(body, dict), f"Expected response body object, got: {body}"
    assert_required_keys(body, UsersEmailTestData.REQUIRED_BODY_KEYS, "response")
    return body


def latest_verification_code(email: str) -> str:
    with DBClient() as db:
        verification = db.get_latest_user_verification(email)

    assert verification, f"Verification code not found for synthetic user: {email}"
    return verification["unique_code"]


def expire_verification_code(code: str) -> None:
    with DBClient() as db:
        expired = db.expire_user_verification_code(code)

    assert expired, "Expected synthetic verification code to be expired"


@pytest_asyncio.fixture(scope="function")
async def approved_email_user() -> dict:
    return await create_approved_user(fullname="Email API Test User")


@pytest_asyncio.fixture(scope="function")
async def existing_email_user() -> dict:
    return await create_approved_user(fullname="Existing Email API Test User")


@pytest_asyncio.fixture(scope="function")
async def auth_client(approved_email_user):
    async with HonoAPIClient() as client:
        await client.login(
            approved_email_user["email"],
            approved_email_user["password"],
        )
        yield client


@pytest.mark.asyncio
async def test_TC_USERS_EMAIL_001_request_email_change_success(
    approved_email_user,
    auth_client,
):
    """
    TC-USERS-EMAIL-001 | Smoke/Security
    Given an approved synthetic user is authenticated
    When PUT /v1/users/me/email with a unique new_email
    Then the email change request is saved
    """
    new_email = UsersEmailTestData.unique_new_email(approved_email_user["email"])
    response = await auth_client.put(
        UsersEmailTestData.EMAIL_PATH,
        json=UsersEmailTestData.change_email_payload(new_email),
    )

    SchemaValidator(response).status_ok().response_time_under(
        UsersEmailTestData.MAX_RESPONSE_MS,
    )
    body = response_body(response)

    assert body.get("code") == UsersEmailTestData.SUCCESS_CODE
    assert body.get("message") == UsersEmailTestData.SAVED_MESSAGE
    assert body.get("data") is None


@pytest.mark.asyncio
async def test_TC_USERS_EMAIL_002_request_email_change_without_token():
    """
    TC-USERS-EMAIL-002 | Security
    Given no bearer token is provided
    When PUT /v1/users/me/email
    Then the API returns 401
    """
    async with HonoAPIClient() as client:
        response = await client.put(
            UsersEmailTestData.EMAIL_PATH,
            json=UsersEmailTestData.change_email_payload(
                "testemailchange+unauth@mailinator.com",
            ),
        )

    SchemaValidator(response).status_unauthorized()


@pytest.mark.asyncio
async def test_TC_USERS_EMAIL_003_request_email_change_rejects_existing_email(
    existing_email_user,
    auth_client,
):
    """
    TC-USERS-EMAIL-003 | Negative
    Given an approved synthetic user is authenticated
    And another approved user already owns the requested email
    When PUT /v1/users/me/email with the existing user's email
    Then the API rejects the duplicate email request
    """
    response = await auth_client.put(
        UsersEmailTestData.EMAIL_PATH,
        json=UsersEmailTestData.change_email_payload(existing_email_user["email"]),
    )

    assert response.status_code == UsersEmailTestData.EXISTING_EMAIL_STATUS, (
        f"Expected duplicate email to return "
        f"{UsersEmailTestData.EXISTING_EMAIL_STATUS}, "
        f"got {response.status_code}: {response.text[:200]}"
    )
    body = response_body(response)
    assert body.get("code") == UsersEmailTestData.EXISTING_EMAIL_CODE
    assert body.get("message") == UsersEmailTestData.EXISTING_EMAIL_MESSAGE
    assert body.get("data") is None


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=True,
    reason=(
        "[DEV-BUG] Screenshot contract documents GET /v1/users/verify-email, "
        "but staging currently returns plain 404 for this route."
    ),
)
async def test_TC_USERS_EMAIL_004_verify_email_change_success(
    approved_email_user,
    auth_client,
):
    """
    TC-USERS-EMAIL-004 | Smoke
    Given an approved synthetic user requested an email change
    When GET /v1/users/verify-email with the latest verification code
    Then the API updates the email successfully
    """
    new_email = UsersEmailTestData.unique_new_email(approved_email_user["email"])
    request_response = await auth_client.put(
        UsersEmailTestData.EMAIL_PATH,
        json=UsersEmailTestData.change_email_payload(new_email),
    )
    SchemaValidator(request_response).status_ok()

    code = latest_verification_code(approved_email_user["email"])
    async with HonoAPIClient() as client:
        response = await client.get(
            UsersEmailTestData.VERIFY_EMAIL_PATH,
            params={"code": code},
        )

    SchemaValidator(response).status_ok().response_time_under(
        UsersEmailTestData.MAX_RESPONSE_MS,
    )
    body = response_body(response)
    assert body.get("code") == UsersEmailTestData.SUCCESS_CODE
    assert body.get("message") == UsersEmailTestData.EMAIL_UPDATED_MESSAGE
    assert body.get("data") is None


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=True,
    reason=(
        "[DEV-BUG] Screenshot contract documents expired-code handling for "
        "GET /v1/users/verify-email, but staging currently returns plain 404."
    ),
)
async def test_TC_USERS_EMAIL_005_verify_email_change_rejects_expired_code(
    approved_email_user,
    auth_client,
):
    """
    TC-USERS-EMAIL-005 | Negative
    Given an approved synthetic user requested an email change
    And the latest verification code is expired in DB
    When GET /v1/users/verify-email with the expired code
    Then the API returns the expired-link response
    """
    new_email = UsersEmailTestData.unique_new_email(approved_email_user["email"])
    request_response = await auth_client.put(
        UsersEmailTestData.EMAIL_PATH,
        json=UsersEmailTestData.change_email_payload(new_email),
    )
    SchemaValidator(request_response).status_ok()

    code = latest_verification_code(approved_email_user["email"])
    expire_verification_code(code)

    async with HonoAPIClient() as client:
        response = await client.get(
            UsersEmailTestData.VERIFY_EMAIL_PATH,
            params={"code": code},
        )

    assert response.status_code == UsersEmailTestData.EXPIRED_STATUS, (
        f"Expected expired verification code to return "
        f"{UsersEmailTestData.EXPIRED_STATUS}, got "
        f"{response.status_code}: {response.text[:200]}"
    )
    body = response_body(response)
    assert body.get("code") == UsersEmailTestData.EXPIRED_CODE
    assert body.get("message") == UsersEmailTestData.EXPIRED_MESSAGE
    assert body.get("data") is None
