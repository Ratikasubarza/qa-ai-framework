# Test file: features/users_account/steps/api/users_account_api_test.py

Suite: Users Account API | Endpoint: GET /v1/users/me/account, PUT /v1/users/me/account
Tests: TC-USERS-ACCOUNT-001 through TC-USERS-ACCOUNT-006 (6 tests)
Requires: approved synthetic user (create_approved_user fixture)

## Test IDs covered
- TC-USERS-ACCOUNT-001 | Smoke | GET account information with valid token → 200 + email matches
- TC-USERS-ACCOUNT-002 | Security | GET account without token → 401
- TC-USERS-ACCOUNT-003 | Regression [DEV-BUG xfail] | Legacy nullable fields — nationality key missing from response
- TC-USERS-ACCOUNT-004 | Smoke | PUT account with valid phone/nationality → 200, then GET reflects updates
- TC-USERS-ACCOUNT-005 | Security | PUT account without token → 401
- TC-USERS-ACCOUNT-006 | Negative | PUT account with invalid phone_code → 422 + NOKUNPROC + "unknown country phone code"

## Known DEV-BUG
- TC-003 is @pytest.mark.xfail(strict=True): /v1/users/me/account omits nationality key
  - Contract expects: {"nationality": null} or {"nationality": {"id":..., "name":..., "iso2":...}}
  - Actual: key is absent from response entirely

## Key test data (UsersAccountTestData)
- ACCOUNT_PATH = APIEndpoints.ME_ACCOUNT = "/v1/users/me/account"
- MAX_RESPONSE_MS = BoundaryValues.MAX_RESPONSE_MS = 3000
- REQUIRED_BODY_KEYS = {"code", "message", "data"}
- REQUIRED_CORE_DATA_KEYS = {"email", "phone_number", "phone_code", "phone_country_iso"}
- CONTRACT_NULLABLE_KEYS = {"phone_country_iso", "nationality"}
- REQUIRED_NATIONALITY_KEYS = {"id", "name", "iso2"}
- SUCCESS_CODE = "OK", SUCCESS_MESSAGE = "Data found", SAVED_MESSAGE = "Data saved"
- INVALID_PHONE_CODE_STATUS = 422, INVALID_PHONE_CODE_RESPONSE_CODE = "NOKUNPROC"
- INVALID_PHONE_CODE_MESSAGE = "unknown country phone code"

## Fixture
- approved_account_user: create_approved_user(fullname="Account API Test User")
- auth_client: HonoAPIClient logged in with approved user credentials
