# Test file: features/cms_users/steps/api/cms_reject_user_test.py

Suite: CMS Reject User API | Endpoint: POST /v1/users/:id/reject
Tests: TC-CMS-REJECT-001 through TC-CMS-REJECT-010 (10 tests)
Requires: cms_token fixture

## Test IDs covered
- TC-CMS-REJECT-001 | Smoke | Register → set_verified(DB) → Reject → DB status=REJECTED
- TC-CMS-REJECT-002 | Boundary | Reject without reason body → 200, 400, or 422
- TC-CMS-REJECT-003 | Boundary | Reject with empty reason "" → 200, 400, or 422
- TC-CMS-REJECT-004 | Security | Reject without CMS token → 401
- TC-CMS-REJECT-005 | Negative | Reject with non-existent user ID → 404 or 400
- TC-CMS-REJECT-006 | Boundary [DEV-BUG] | Reject APPROVED user — business rule unclear
- TC-CMS-REJECT-007 | Boundary [DEV-BUG] | Double reject (idempotent check) → 200, 400, or 409
- TC-CMS-REJECT-008 | Edge [DEV-BUG] | Reject PENDING unverified user → 200, 400, or 422
- TC-CMS-REJECT-009 | Boundary | Reject with 1200-char reason → 200, 400, or 422
- TC-CMS-REJECT-010 | Combination [DEV-BUG] | Reject then approve same user

## Known DEV-BUGs in this suite
1. TC-006: Should rejecting an APPROVED user be allowed? Business rule unclear.
2. TC-007: Double reject — should be idempotent or return error?
3. TC-008: Should admin be able to reject unverified PENDING users?
4. TC-010: Should a rejected user be approvable? Business rule unclear.

## Helper _register_and_verify()
1. RegisterTestData.valid_payload() → POST /v1/users/register
2. DBClient.get_user_by_email() → get user ID
3. DBClient.set_verified(email) → promote to verified state
Returns: {"email": ..., "user_id": ...}
