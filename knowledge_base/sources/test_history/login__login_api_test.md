# Test file: features/login/steps/api/login_api_test.py

Suite: Login API | Endpoint: POST /v1/users/login, GET /v1/users/me, GET /v1/search/posts
Tests: TC-API-001 through TC-API-020 (20 tests)
Marks: smoke, sanity, regression, security, boundary, performance, negative, api

## Test IDs covered
- TC-API-001 | Smoke | Valid credentials return 200 + accessToken
- TC-API-002 | Sanity | Wrong password returns 401
- TC-API-003 | Sanity | Invalid email format returns 400/422
- TC-API-004 | Sanity | Missing password returns 400/422
- TC-API-005 | Regression | Empty body returns 400/422
- TC-API-006 | Regression | Search with auth token returns 200/400
- TC-API-007 | Sanity | Search without auth returns 401/403
- TC-API-008 | Regression | Empty search query returns 200/400/422
- TC-API-009 | Performance | Search response under SLA (3000ms)
- TC-API-010 | Smoke | Get profile with valid token returns 200
- TC-API-011 | Security | Get profile without token returns 401
- TC-API-012 | Security | Login without x-api-key header returns 401/403
- TC-API-013 | Negative | Login with empty email returns 400/422
- TC-API-014 | Negative | Login with empty password returns 4xx
- TC-API-016 | Performance | Login response time under 3s
- TC-API-017 | Security | SQL injection in email is blocked
- TC-API-018 | Boundary | 500-char email is handled gracefully
- TC-API-019 | Boundary | Uppercase email — documents case sensitivity
- TC-API-020 | Security | Three consecutive wrong-password attempts all return 401

## Key fixtures
- auth_client: logged-in HonoAPIClient (scope=function)
- unauth_client: unauthenticated HonoAPIClient (scope=function)

## Credentials
- EMAIL: STAGING_EMAIL env var (default testingHonoA@mailinator.com)
- PASSWORD: STAGING_PASSWORD env var

## Assertions used
- SchemaValidator(response).status_ok().has_key("data").response_time_under(3000)
- response.status_code in [400, 401, 422]
- token found in data.accessToken or data.token
