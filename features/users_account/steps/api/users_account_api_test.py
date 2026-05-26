"""User account API tests — GET and PUT /v1/users/me/account."""
import allure
import pytest
import pytest_asyncio


from core.db.db_client import DBClient
from core.db.test_user_helper import create_approved_user_sync
from core.test_data.cleanup_registry import cleanup_registry
from features.users_account.test_data.users_account_test_data import (
    UsersAccountTestData,
)
from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator
from skills.testing.helpers import assert_required_keys

pytestmark = [
    allure.feature("Users - Account"),
    allure.suite("API"),
]


def get_account_payload(response) -> tuple[dict, dict]:
    body = response.json()
    assert isinstance(body, dict), f"Expected response body object, got: {body}"
    assert_required_keys(body, UsersAccountTestData.REQUIRED_BODY_KEYS, "response")

    data = body.get("data")
    assert isinstance(data, dict), f"Expected data object, got: {body}"
    assert_required_keys(data, UsersAccountTestData.REQUIRED_CORE_DATA_KEYS, "account")
    return body, data


@pytest.fixture(scope="module")
def approved_account_user() -> dict:
    """Create one approved user for the whole module — sync pattern matches conftest_shared_fixtures."""
    user = create_approved_user_sync(fullname="Account API Test User")
    user_id = user["user_id"]
    cleanup_registry.register(
        entity_type="user",
        entity_id=user_id,
        cleanup_fn=lambda: _delete_user(user_id),
    )
    return user


def _delete_user(user_id: str) -> None:
    with DBClient() as db:
        db.delete_user(user_id)


@pytest_asyncio.fixture(scope="function")
async def auth_client(approved_account_user):
    async with HonoAPIClient() as client:
        await client.login(
            approved_account_user["email"],
            approved_account_user["password"],
        )
        yield client


@pytest.mark.asyncio
async def test_TC_USERS_ACCOUNT_001_get_account_information_success(
    approved_account_user,
    auth_client,
):
    """
    TC-USERS-ACCOUNT-001 | Smoke
    Given an approved synthetic user is authenticated
    When GET /v1/users/me/account
    Then account information is returned for the authenticated user
    """
    response = await auth_client.get(UsersAccountTestData.ACCOUNT_PATH)

    SchemaValidator(response).status_ok().response_time_under(
        UsersAccountTestData.MAX_RESPONSE_MS,
    )
    body, data = get_account_payload(response)

    assert body.get("code") == UsersAccountTestData.SUCCESS_CODE
    assert body.get("message") == UsersAccountTestData.SUCCESS_MESSAGE
    assert data.get("email") == approved_account_user["email"]


@pytest.mark.asyncio
async def test_TC_USERS_ACCOUNT_002_get_account_without_token():
    """
    TC-USERS-ACCOUNT-002 | Security
    Given no bearer token is provided
    When GET /v1/users/me/account
    Then the API returns 401
    """
    async with HonoAPIClient() as client:
        response = await client.get(UsersAccountTestData.ACCOUNT_PATH)

    SchemaValidator(response).status_unauthorized()


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=True,
    reason=(
        "[DEV-BUG] /v1/users/me/account omits nationality; contract expects "
        "the key to exist with object or null value."
    ),
)
async def test_TC_USERS_ACCOUNT_003_account_optional_fields_allow_legacy_nulls(
    auth_client,
):
    """
    TC-USERS-ACCOUNT-003 | Regression
    Given an authenticated user exists
    When GET /v1/users/me/account
    Then legacy nullable metadata remains contract-safe
    """
    response = await auth_client.get(UsersAccountTestData.ACCOUNT_PATH)

    SchemaValidator(response).status_ok()
    _, data = get_account_payload(response)

    assert_required_keys(
        data,
        UsersAccountTestData.CONTRACT_NULLABLE_KEYS,
        "nullable account contract",
    )

    phone_country_iso = data.get("phone_country_iso")
    assert phone_country_iso is None or isinstance(phone_country_iso, str)

    nationality = data.get("nationality")
    assert nationality is None or isinstance(nationality, dict)
    if isinstance(nationality, dict):
        assert_required_keys(
            nationality,
            UsersAccountTestData.REQUIRED_NATIONALITY_KEYS,
            "nationality",
        )


@pytest.mark.asyncio
async def test_TC_USERS_ACCOUNT_004_update_account_information_success(
    approved_account_user,
    auth_client,
):
    """
    TC-USERS-ACCOUNT-004 | Smoke
    Given an approved synthetic user is authenticated
    When PUT /v1/users/me/account with valid phone and country metadata
    Then the API saves the account update and GET reflects phone metadata
    """
    response = await auth_client.put(
        UsersAccountTestData.ACCOUNT_PATH,
        json=UsersAccountTestData.valid_update_payload(approved_account_user["email"]),
    )

    SchemaValidator(response).status_ok().response_time_under(
        UsersAccountTestData.MAX_RESPONSE_MS,
    )
    body = response.json()
    assert body.get("code") == UsersAccountTestData.SUCCESS_CODE
    assert body.get("message") == UsersAccountTestData.SAVED_MESSAGE
    assert body.get("data") is None

    get_response = await auth_client.get(UsersAccountTestData.ACCOUNT_PATH)
    SchemaValidator(get_response).status_ok()
    _, data = get_account_payload(get_response)

    update_payload = UsersAccountTestData.valid_update_payload(
        approved_account_user["email"],
    )
    assert data.get("phone_number") == update_payload["phone_number"]
    assert data.get("phone_code") == update_payload["phone_code"]


@pytest.mark.asyncio
async def test_TC_USERS_ACCOUNT_005_update_account_without_token():
    """
    TC-USERS-ACCOUNT-005 | Security
    Given no bearer token is provided
    When PUT /v1/users/me/account
    Then the API returns 401
    """
    async with HonoAPIClient() as client:
        response = await client.put(
            UsersAccountTestData.ACCOUNT_PATH,
            json=UsersAccountTestData.valid_update_payload("synthetic.user@example.com"),
        )

    SchemaValidator(response).status_unauthorized()


@pytest.mark.asyncio
async def test_TC_USERS_ACCOUNT_006_update_account_rejects_invalid_phone_code(
    approved_account_user,
    auth_client,
):
    """
    TC-USERS-ACCOUNT-006 | Negative
    Given an approved synthetic user is authenticated
    When PUT /v1/users/me/account with invalid phone_code
    Then the API returns an exact validation error without forcing a workaround
    """
    response = await auth_client.put(
        UsersAccountTestData.ACCOUNT_PATH,
        json=UsersAccountTestData.invalid_phone_code_payload(
            approved_account_user["email"],
        ),
    )

    assert response.status_code == UsersAccountTestData.INVALID_PHONE_CODE_STATUS, (
        f"Expected invalid phone code to return "
        f"{UsersAccountTestData.INVALID_PHONE_CODE_STATUS}, got "
        f"{response.status_code}: {response.text[:200]}"
    )
    body = response.json()
    assert body.get("code") == UsersAccountTestData.INVALID_PHONE_CODE_RESPONSE_CODE
    assert body.get("message") == UsersAccountTestData.INVALID_PHONE_CODE_MESSAGE
    assert body.get("data") is None
