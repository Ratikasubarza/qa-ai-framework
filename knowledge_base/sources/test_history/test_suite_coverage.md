# Test Suite Coverage — Hono QA Framework

## Summary
Total tests: 216+ across 24 suites.
Platforms covered: API, Web, Android mobile.
Framework: pytest + asyncio + Allure reporting.

## Login API (19 tests) — features/login/steps/api/login_api_test.py
Covers: valid login, wrong password, invalid email, missing fields, empty body,
search authenticated/unauthenticated, profile GET/unauth, no API key,
empty email/password, response time SLA, SQL injection, long email, case sensitivity,
multiple failed attempts rate limiting.
Pattern: uses SchemaValidator, HonoAPIClient, static STAGING_EMAIL/PASSWORD from env.

## Register API (30 tests) — features/register/steps/api/register_api_test.py
Covers: valid registration, duplicate email/phone, missing fields, invalid email/phone format,
combination tests (duplicate+valid pairs), SQL injection, XSS, long fullname,
invalid country code, phone length boundaries, LinkedIn URL validation,
empty/whitespace fullname, same user twice, null values.
Pattern: RegisterTestData.valid_payload() with timestamp suffix for unique data.
Uses skip_on_email_quota() guard for Resend quota limit.

## Create Post API (16 tests) — features/posts/steps/api/create_post_api_test.py
Covers: valid post, media attachment, anonymous post, multiple topics (3),
schema validation (engagement counts = 0), visibility=EVERYONE,
no auth token (401), no API key (401), empty topic_ids (422 NOKUNPROC),
empty content, missing content, invalid visibility, missing topic_ids,
long content (5000 chars), empty body, response time SLA.
Pattern: post_token fixture (module scope, create_approved_user_sync),
_create_post() helper, APIAssertions chainable assertions.
Fixture setup: creates real user via DB (requires VPN/DB connection).

## Onboarding API (28 tests) — features/onboarding/steps/api/onboarding_api_test.py
Covers: full onboarding flow, field validation (with known DEV-BUG gaps),
industry/business/interest/social cause IDs, nationality, city, role, company.
Known gaps: empty body accepted, missing fields not validated, invalid IDs return 500.

## CMS Login API — features/cms_login/steps/api/cms_login_api_test.py
CMS admin login with resource=admin. Standard admin credential tests.

## CMS Users API — features/cms_users/steps/api/cms_users_api_test.py
List users: pagination, status filter, ordering. Admin-only endpoint.

## CMS Approve User — features/cms_users/steps/api/cms_approve_user_test.py
Approve workflow: PENDING → APPROVED. Edge cases: already approved, not found.
Known bug: approves unverified email users [BUG-007].

## CMS Reject User — features/cms_users/steps/api/cms_reject_user_test.py
Reject workflow with known DEV-BUGs: reject approved user, double reject, reject unverified.

## Users Account API — features/users_account/steps/api/users_account_api_test.py
GET/PUT /v1/users/me/account. nationality field xfail [DEV-BUG-002].

## Users Email API — features/users_email/steps/api/users_email_api_test.py
Email change request and verification. GET /v1/users/verify-email xfail (404) [DEV-BUG-001].

## Users Password API — features/users_password/steps/api/users_password_api_test.py
Password change: valid, wrong current, weak new password.

## Login Mobile (Android) — features/login/steps/mobile/login_android_test.py
Appium-based Android tests. Uses LoginScreen(BaseMobileScreen) POM.
Requires: Appium server + Android device/emulator.

## Register Mobile (Android) — features/register/steps/mobile/register_android_test.py
Appium registration flow.

## Onboarding Mobile (Android) — features/onboarding/steps/mobile/onboarding_android_test.py
Multi-step onboarding flow on Android.

## Login Web App — features/login/steps/web/login_web_app_test.py
Playwright-based web tests for app-dev.thehono.com.
Uses LoginPage(BasePage) POM.

## Test Execution History
- Last full run: 127 passed, 3 xfailed, 18 deselected (268.14s)
- xfailed: TC-USERS-ACCOUNT-003 (nationality), TC-USERS-EMAIL-004/005 (verify-email 404)
- deselected: mobile + web tests (requires device/browser; excluded in CI API-only runs)
- Run command: PYTHONPATH=. ./venv/bin/python3.11 -m pytest features/ -v --ignore=features/login/steps/mobile --ignore=features/login/steps/web --ignore=features/register/steps/mobile --ignore=features/onboarding/steps/mobile

## Fixture Patterns
- Module-scoped user fixtures: post_token, (onboarding uses similar pattern)
- Function-scoped CMS fixtures: cms_token (re-authenticates each test)
- Static credentials: LOGIN tests use STAGING_EMAIL / STAGING_PASSWORD from .env
- Dynamic users: posts, onboarding use create_approved_user_sync() via DB (requires VPN)
