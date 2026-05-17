# Test file: features/cms_users/steps/api/cms_users_api_test.py

Suite: CMS Users API | Endpoint: GET /v1/users
Tests: TC-CMS-USERS-001 through TC-CMS-USERS-012 (12+ tests)
Requires: cms_token fixture (CMS admin Bearer token)

## Test IDs covered
- TC-CMS-USERS-001 | Smoke | GET /v1/users with valid token → 200, list of users with id/name/email/status
- TC-CMS-USERS-002 | Security | GET without token → 401
- TC-CMS-USERS-003 | Functional | Filter by status=APPROVED → all users have APPROVED status
- TC-CMS-USERS-004 | Functional | Pagination page=1 size=5 → ≤5 users returned
- TC-CMS-USERS-005 | Functional | orderBy=name order=DESC → 200
- TC-CMS-USERS-006 | Functional | Different page sizes (5, 10, 50) → correct count returned
- TC-CMS-USERS-007 | Functional | orderBy=created_at, order=ASC and DESC → 200
- TC-CMS-USERS-008 | Functional | Page 1 and page 2 with same size → no overlapping users
- TC-CMS-USERS-009 | Functional | Filter by status 1 (PENDING), 2 (APPROVED), 3 (REJECTED) → 200
- TC-CMS-USERS-010 | Boundary | No query params → API uses defaults → 200 + list
- TC-CMS-USERS-011 | Boundary | Invalid page=-1 → graceful (200 or 400)
- TC-CMS-USERS-012 | Boundary | Invalid order=INVALID → graceful (200 or 400)

## Endpoint details
- Path: GET /v1/users (APIEndpoints.USERS_LIST)
- Query params: page (default 1), size (default 20), orderBy (name|created_at), order (ASC|DESC), status (1|2|3)
- Response: {data: [{id, name, email, status}, ...]}
- Status values: 1=PENDING, 2=APPROVED, 3=REJECTED
