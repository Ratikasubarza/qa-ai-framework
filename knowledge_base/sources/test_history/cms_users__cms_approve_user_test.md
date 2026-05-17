# Test file: features/cms_users/steps/api/cms_approve_user_test.py

Suite: CMS Approve User API | Endpoint: POST /v1/users/:id/approve
Tests: TC-CMS-APPROVE-001 through TC-CMS-APPROVE-005 (5 tests)
Requires: cms_token fixture (CMS admin Bearer token)

## Test IDs covered
- TC-CMS-APPROVE-001 | Smoke | Full E2E: Register → DB set_verified → CMS approve → DB status=APPROVED
- TC-CMS-APPROVE-002 | Negative | Approve PENDING user (not verified) → 200, 400, or 422
- TC-CMS-APPROVE-003 | Negative | Approve non-existent user ID (00000000-0000-...) → 404 or 400
- TC-CMS-APPROVE-004 | Security | Approve without CMS token → 401
- TC-CMS-APPROVE-005 | Boundary | Approve already APPROVED user → 200, 400, or 409

## Flow used in TC-CMS-APPROVE-001
1. RegisterTestData.valid_payload() → POST /v1/users/register
2. DBClient.get_user_by_email() → assert status=PENDING
3. DBClient.set_verified(email) → promote to verified state
4. POST /v1/users/:id/approve with CMS Bearer token
5. DBClient.get_user_by_email() → assert status=APPROVED + approved_at not null

## Key helpers
- APIEndpoints.approve(user_id) → f"/v1/users/{user_id}/approve"
- create_approved_user_sync() via core.db.test_user_helper
- DBClient.set_verified(email): updates DB directly (bypasses email flow)
