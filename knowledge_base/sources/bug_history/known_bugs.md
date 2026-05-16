# Hono App — Known Bugs & Past Issues

## [DEV-BUG-001] GET /v1/users/verify-email returns 404
- **Severity**: P2
- **Status**: Open
- **Endpoint**: GET /v1/users/verify-email
- **Description**: API contract documents email verification via GET request with code param,
  but staging currently returns 404 for this route.
- **Impact**: Email change verification flow untestable via API.
- **Workaround**: xfail marker on tests TC-USERS-EMAIL-004 and TC-USERS-EMAIL-005.

## [DEV-BUG-002] GET /v1/users/me/account omits nationality field
- **Severity**: P2
- **Status**: Open
- **Endpoint**: GET /v1/users/me/account
- **Description**: Response body omits the `nationality` key entirely.
  Contract expects key to exist with object or null value.
- **Impact**: Test TC-USERS-ACCOUNT-003 marked xfail.

## [DEV-BUG-003] Reject already-approved user behavior unclear
- **Severity**: P3
- **Status**: Under discussion
- **Endpoint**: POST /v1/users/:id/reject
- **Description**: API accepts reject on APPROVED user without clear error.
  Business rule: should APPROVED users be rejectable?
- **Impact**: TC-CMS-REJECT-006 documents actual behavior only.

## [DEV-BUG-004] Double reject idempotency
- **Severity**: P3
- **Status**: Under discussion
- **Endpoint**: POST /v1/users/:id/reject
- **Description**: Rejecting an already-REJECTED user returns 200 in some cases.
  Expected: 409 Conflict or idempotent 200 with stable state.
- **Impact**: TC-CMS-REJECT-007 documents actual behavior.

## [BUG-005] Resend email quota — 500 response masquerades as server error
- **Severity**: P2 (platform constraint)
- **Status**: Known / By Design
- **Description**: When Resend daily quota is exhausted, /v1/users/register returns 500
  with body: "You have reached your daily email sending quota."
  Should return 503 or 429 to be clearly distinguishable from server errors.
- **Impact**: Test suite skips register-dependent tests daily after quota exhausted.

## [BUG-006] Login 401 — intermittent on staging environment
- **Severity**: P2
- **Status**: Monitoring
- **Description**: POST /v1/users/login occasionally returns 401 for valid credentials
  when staging DB is under load. Reproduces ~5% of runs.
- **Root cause**: Connection pool exhaustion on staging MySQL.
- **Workaround**: Retry logic in test_user_helper.

## [BUG-007] CMS approve unverified user returns 200
- **Severity**: P2
- **Status**: Open
- **Endpoint**: POST /v1/users/:id/approve
- **Description**: API allows approving a PENDING user who has not verified email.
  Expected: 400 "User must verify email before approval."
- **Impact**: TC-CMS-APPROVE-002 documents this gap.
