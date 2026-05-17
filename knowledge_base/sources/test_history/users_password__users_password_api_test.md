# Test file: features/users_password/steps/api/users_password_api_test.py

Suite: Users Password API | Endpoint: PUT /v1/users/me/password
Tests: TC-USERS-PASSWORD-001 through TC-USERS-PASSWORD-004 (4 tests + parametrize)
Requires: approved synthetic user, DBClient for password reset

## Test IDs covered
- TC-USERS-PASSWORD-001 | Smoke/Security | Change password → old rejected, new accepted; then DB reset
- TC-USERS-PASSWORD-002 | Security | PUT without token → 401
- TC-USERS-PASSWORD-003 | Negative | Wrong current_password → 400/401/422 + original password still works
- TC-USERS-PASSWORD-004 | Boundary/Negative | Missing current_password OR new_password → 400/422
  (parametrized: missing_current_password, missing_new_password)

## Key test data (UsersPasswordTestData)
- CURRENT_PASSWORD: known current password set in DB (stable constant)
- NEW_PASSWORD: new password used in TC-001
- valid_change_payload(): {"current_password": CURRENT_PASSWORD, "new_password": NEW_PASSWORD}
- wrong_current_payload(): {"current_password": "WrongPass", "new_password": NEW_PASSWORD}
- missing_current_password_payload(): {"new_password": NEW_PASSWORD}
- missing_new_password_payload(): {"current_password": CURRENT_PASSWORD}
- set_known_password(email): DB override to guarantee known password state
- reset_password(email): DB reset after TC-001 so user remains reusable

## Fixture
- approved_password_user: create_approved_user(password=UsersPasswordTestData.CURRENT_PASSWORD)
  + set_known_password(email) for DB sync
- auth_client: HonoAPIClient logged in with CURRENT_PASSWORD

## Helper login_status(email, password)
Returns HTTP status code of a login attempt (for verifying old/new password behavior).
