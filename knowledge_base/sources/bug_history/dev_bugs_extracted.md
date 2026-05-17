# DEV-BUG Comments — Extracted from Test Files (Updated 2026-05-16)

## Summary
Total DEV-BUG entries: 30+ across 5 files.
These represent known API behavioral issues discovered during QA testing.

## Onboarding API [PUT /v1/users/onboarding]

### [DEV-BUG] Missing full_name not validated
- File: features/onboarding/steps/api/onboarding_api_test.py
- Test: TC-ONBOARDING-*
- Description: API does not validate missing full_name — returns 200 instead of 400.
  Validation gap: required field accepted as absent.

### [DEV-BUG] Missing city_id not validated
- File: features/onboarding/steps/api/onboarding_api_test.py
- Description: API does not validate missing city_id — returns 200. Should return 400/422.

### [DEV-BUG] Invalid city_id returns 500 with raw DB error
- File: features/onboarding/steps/api/onboarding_api_test.py
- Description: Invalid city_id triggers foreign key constraint error exposed as 500.
  Should return 400/422 with friendly message.
- Severity: P1 (exposes internal DB error messages)

### [DEV-BUG?] 3 industry_ids accepted when max is 2
- File: features/onboarding/steps/api/onboarding_api_test.py
- Description: API spec says max 2 industry_ids, but API accepts 3. Business rule unclear.

### [DEV-BUG] Invalid industry IDs return 500
- File: features/onboarding/steps/api/onboarding_api_test.py
- Description: Invalid industry ID values cause 500 due to foreign key constraint.
  Should return 400/422.

### [DEV-BUG] Empty body accepted with 200
- File: features/onboarding/steps/api/onboarding_api_test.py
- Description: PUT /v1/users/onboarding accepts {} and returns 200. Should validate required fields.

## CMS Reject User [POST /v1/users/{id}/reject]

### [DEV-BUG] Reject already-approved user returns 200 without clear error
- File: features/cms_users/steps/api/cms_reject_user_test.py
- Test: TC-CMS-REJECT-006
- Description: Business rule unclear — should APPROVED users be rejectable?
  API returns 200 without validating prior approval state.

### [DEV-BUG] Double reject — idempotency undefined
- File: features/cms_users/steps/api/cms_reject_user_test.py
- Test: TC-CMS-REJECT-007
- Description: Rejecting already-REJECTED user returns 200. Expected: 409 Conflict or
  clearly idempotent 200 with stable state.

### [DEV-BUG] Reject unverified user — business rule unclear
- File: features/cms_users/steps/api/cms_reject_user_test.py
- Description: Should admin be able to reject users who haven't verified email?
  API allows it but requirement is ambiguous.

### [DEV-BUG] Rejected user re-approvable — business rule unclear
- File: features/cms_users/steps/api/cms_reject_user_test.py
- Description: Rejected user can be approved again. Flow: approve → reject → approve.
  Business constraint not enforced.

## Users Account [GET /v1/users/me/account]

### [DEV-BUG] nationality field missing from GET response
- File: features/users_account/steps/api/users_account_api_test.py
- Test: TC-USERS-ACCOUNT-003 (xfail)
- Description: API contract (api_spec.yaml) documents nationality as nullable object in
  GET /v1/users/me/account response. Actual response omits the key entirely.
  Tests that assert nationality key existence are marked xfail.

## Users Email [GET /v1/users/verify-email / PUT /v1/users/me/email]

### [DEV-BUG] GET /v1/users/verify-email returns 404
- File: features/users_email/steps/api/users_email_api_test.py
- Tests: TC-USERS-EMAIL-004, TC-USERS-EMAIL-005 (xfail)
- Description: Email verification endpoint documented in screenshot contract but returns 404.
  Email change verification flow completely untestable via API.

### [DEV-BUG] Expired verification code — handling unclear
- File: features/users_email/steps/api/users_email_api_test.py
- Description: Expired-code scenario documented in screenshot contract.
  Behavior on staging not verifiable (endpoint returns 404).

## Platform Bugs (not DEV-BUG but test-impacting)

### [BUG-005] Resend quota: /v1/users/register returns 500 when quota exhausted
- Impact: Test suite auto-skips register-dependent tests when skip_on_email_quota() fires.
- Helper: skills/testing/helpers.py skip_on_email_quota()

### [BUG-006] Login 401 intermittent on staging
- Root cause: MySQL connection pool exhaustion under staging load (~5% failure rate)
- Workaround: retry logic in core/db/test_user_helper.py create_approved_user_sync()
