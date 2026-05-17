# Hono App — Gherkin BDD Scenarios — Updated 2026-05-16

## Feature files indexed (17 total)
- login/api, login/web, login/mobile (android, ios, cms)
- register/api, register/mobile
- cms_login/api
- cms_users/api (approve, reject, list)
- onboarding/api, onboarding/mobile
- posts/api
- users_account/api
- users_email/api
- users_password/api

## Feature: Login API — POST /v1/users/login
Tags: @api @login
- @smoke @P0 TC-LOGIN-001 Valid credentials return 200 + accessToken
- @smoke @P0 TC-LOGIN-002 Wrong password returns 401
- @negative @P1 TC-LOGIN-003 Invalid email format returns 400/422
- @negative @P1 TC-LOGIN-004 Missing password returns 400/422
- @boundary @P2 TC-LOGIN-005 Empty body returns 400/422
- @security @P0 TC-LOGIN-012 Without x-api-key returns 401
- @negative @P1 TC-LOGIN-013 Empty email returns 400/422
- @negative @P1 TC-LOGIN-014 Empty password returns 400/422
- @performance @P2 TC-LOGIN-016 Response time under 3000ms
- @security @P0 TC-LOGIN-017 SQL injection in email is blocked
- @boundary @P2 TC-LOGIN-018 500-char email handled gracefully
- @boundary @P2 TC-LOGIN-019 Uppercase email — documents case sensitivity
- @security @P1 TC-LOGIN-020 Three consecutive wrong-password attempts all return 401

## Feature: Register API — POST /v1/users/register
Tags: @api @register
- @smoke @P0 TC-REG-API-001 Valid data returns 200 with code=OK
- @negative @P1 TC-REG-API-002 Duplicate email returns 4xx
- @boundary @P1 TC-REG-API-003 Missing required fields returns 400/422
- @negative @P1 TC-REG-API-004 Invalid email format returns 400/422
- @boundary @P1 TC-REG-API-005 Empty body returns 400/422
- @negative @P1 TC-REG-API-006 Duplicate email blocked
- @negative @P1 TC-REG-API-007 Duplicate phone number blocked
- @combination @P2 TC-REG-API-008 Duplicate email + valid phone → blocked
- @combination @P2 TC-REG-API-009 Valid email + duplicate phone → blocked
- @negative @P1 TC-REG-API-010 Invalid email format (multiple forms) blocked
- @negative @P1 TC-REG-API-011 Non-numeric phone number returns 400/422
- @security @P0 TC-REG-API-012 Missing x-api-key returns 401/403
- @security @P0 TC-REG-API-013 SQL injection in fullname sanitized
- @boundary @P2 TC-REG-API-014 Very long fullname (500+ chars) documented
- @combination @P2 TC-REG-API-015 Both email and phone duplicate → blocked
- @boundary @P1 TC-REG-API-016 Minimum valid data returns 200
- @boundary @P2 TC-REG-API-017 Special chars in fullname documented
- @negative @P1 TC-REG-API-018 Missing fullname returns 400/422
- @boundary @P2 TC-REG-API-019 Missing linkedin documents behavior
- @negative @P1 TC-REG-API-020 Invalid phone country code returns 400/422
- @boundary @P2 TC-REG-API-021 Phone too short (3 digits) returns 400/422
- @boundary @P2 TC-REG-API-022 Phone too long (21 digits) documented
- @security @P1 TC-REG-API-023 XSS in fullname handled safely
- @boundary @P2 TC-REG-API-024 Valid LinkedIn URL accepted
- @negative @P1 TC-REG-API-025 Invalid LinkedIn URL documented
- @performance @P2 TC-REG-API-026 Response time under 3000ms
- @boundary @P2 TC-REG-API-027 Empty string fullname returns 400/422
- @boundary @P2 TC-REG-API-028 Whitespace-only fullname documented
- @combination @P2 TC-REG-API-029 Same user registered twice → second blocked
- @combination @P2 TC-REG-API-030 Null values in required fields returns 400/422

## Feature: Create Post API — POST /v1/posts
Tags: @api @posts
- @smoke @P0 TC-POST-API-001 Valid post creation returns 200 with post id
- @smoke @P0 TC-POST-API-002 Create post with media attachment returns 200
- @boundary @P1 TC-POST-API-003 Create anonymous post sets is_anonymous=true
- @boundary @P1 TC-POST-API-004 Create post with 3 topic_ids returns topics array
- @smoke @P0 TC-POST-API-005 Response contains all required fields + engagement counts=0
- @boundary @P2 TC-POST-API-006 Visibility=EVERYONE accepted
- @security @P0 TC-POST-API-007 Without auth token returns 401
- @security @P0 TC-POST-API-008 Without x-api-key returns 401
- @negative @P1 TC-POST-API-009 Empty topic_ids returns 422 NOKUNPROC
- @negative @P1 TC-POST-API-010 Empty content returns 400/422
- @negative @P1 TC-POST-API-011 Missing content field returns 400/422
- @negative @P1 TC-POST-API-012 Invalid visibility returns 400/422
- @negative @P1 TC-POST-API-013 Missing topic_ids field returns 400/422
- @boundary @P2 TC-POST-API-014 5000-char content documents limit
- @boundary @P2 TC-POST-API-015 Empty body returns 400/422
- @performance @P2 TC-POST-API-016 Response time under 3000ms
- @combination @P2 TC-POST-API-017 Mention user who disabled tagging returns 422 NOKUNPROC

## Feature: CMS Login API — POST /v1/users/login?resource=admin
Tags: @api @cms-login
- Admin login with resource=admin returns 200 + accessToken
- Login without resource=admin returns 401
- Invalid CMS credentials returns 401

## Feature: CMS Users API — GET /v1/users
Tags: @api @cms-users
- List users with admin token returns 200 + array
- Filter by status (PENDING/APPROVED/REJECTED) works
- Pagination (page, size) works
- Without admin token returns 401

## Feature: CMS Approve User — POST /v1/users/{id}/approve
Tags: @api @cms-approve
- Approve PENDING user returns 200
- Approve non-existent user returns 404
- Approve already-approved user (idempotency)
- Without admin token returns 401

## Feature: CMS Reject User — POST /v1/users/{id}/reject
Tags: @api @cms-reject
- Reject PENDING user returns 200
- Reject with reason payload
- Double reject idempotency [DEV-BUG-004]
- Without admin token returns 401

## Feature: Onboarding API — PUT /v1/users/onboarding
Tags: @api @onboarding
- Complete onboarding with all fields returns 200
- Minimum required fields accepted
- Missing required fields — API accepts (validation gap) [DEV-BUG]
- Industry IDs: 1–2 items; invalid IDs return 500 [DEV-BUG]
- city_id validation missing [DEV-BUG]

## Feature: Users Account API — GET/PUT /v1/users/me/account
Tags: @api @users-account
- GET account returns email, phone, nationality
- PUT account updates phone successfully
- nationality field omitted in GET [DEV-BUG-002]

## Feature: Users Email API — PUT /v1/users/me/email
Tags: @api @users-email
- Request email change returns 200
- Duplicate new_email returns 422
- Verify email GET /v1/users/verify-email returns 404 [DEV-BUG-001]

## Feature: Users Password API — PUT /v1/users/me/password
Tags: @api @users-password
- Change password with valid current password returns 200
- Wrong current password returns 400
- Weak/short new password returns 400/422
