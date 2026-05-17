# Test file: features/users_email/steps/api/users_email_api_test.py

Suite: Users Email API | Endpoint: PUT /v1/users/me/email, GET /v1/users/verify-email
Tests: TC-USERS-EMAIL-001 through TC-USERS-EMAIL-005 (5 tests)
Requires: approved synthetic user (create_approved_user fixture), DBClient for verification codes

## Test IDs covered
- TC-USERS-EMAIL-001 | Smoke | PUT email change with unique new_email → 200, code=OK, message="Data saved"
- TC-USERS-EMAIL-002 | Security | PUT email change without token → 401
- TC-USERS-EMAIL-003 | Negative | PUT email change to existing user's email → 422, code=NOKUNPROC, "email already exists"
- TC-USERS-EMAIL-004 | Smoke [DEV-BUG xfail] | GET verify-email with valid code → 200 but staging returns 404
- TC-USERS-EMAIL-005 | Negative [DEV-BUG xfail] | GET verify-email with expired code → 410 but staging returns 404

## Known DEV-BUGs (both xfail strict=True)
- TC-004: GET /v1/users/verify-email returns plain 404 in staging (route not found)
  - Expected: 200, message="Email updated successfully"
- TC-005: GET /v1/users/verify-email with expired code returns 404 in staging
  - Expected: 410, message="Verification link has expired"

## Key test data (UsersEmailTestData)
- EMAIL_PATH = APIEndpoints.ME_EMAIL = "/v1/users/me/email"
- VERIFY_EMAIL_PATH = APIEndpoints.VERIFY_EMAIL = "/v1/users/verify-email"
- MAX_RESPONSE_MS = BoundaryValues.MAX_RESPONSE_MS = 3000
- REQUIRED_BODY_KEYS = {"code", "message", "data"}
- SUCCESS_CODE = "OK", SAVED_MESSAGE = "Data saved"
- EMAIL_UPDATED_MESSAGE = "Email updated successfully"
- EXISTING_EMAIL_STATUS = 422, EXISTING_EMAIL_CODE = "NOKUNPROC"
- EXISTING_EMAIL_MESSAGE = "email already exists"
- EXPIRED_STATUS = 410, EXPIRED_CODE = "EXPIRED", EXPIRED_MESSAGE = "Verification link has expired"

## DB helpers used
- db.get_latest_user_verification(email) → get verification code from DB
- db.expire_user_verification_code(code) → expire code in DB (for TC-005)
