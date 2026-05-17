# Test file: features/cms_login/steps/api/cms_login_api_test.py

Suite: CMS Login API | Endpoint: POST /v1/users/login (resource: admin)
Tests: TC-CMS-API-001 through TC-CMS-API-010 (10 tests)

## Test IDs covered
- TC-CMS-API-001 | Smoke | CMS login with valid credentials returns accessToken (200)
- TC-CMS-API-002 | Negative | Wrong password returns 401/400
- TC-CMS-API-003 | Boundary | Missing resource field returns 4xx
- TC-CMS-API-004 | Negative | Wrong resource value returns 4xx
- TC-CMS-API-005 | Performance | CMS login response under 3s (MAX_RESPONSE_MS)
- TC-CMS-API-006 | Security | Login without x-api-key returns 401/403
- TC-CMS-API-007 | Negative | Invalid email format returns 400/422
- TC-CMS-API-008 | Negative | Empty email returns 400/422
- TC-CMS-API-009 | Negative | Empty password returns 4xx
- TC-CMS-API-010 | Boundary | 3 consecutive wrong-password attempts all blocked

## Key test data (CmsLoginTestData)
- VALID_EMAIL: CMS admin email from env
- VALID_PASSWORD: CMS admin password from env
- RESOURCE: "admin"
- INVALID_EMAIL: "not-an-email"
- EMPTY_STRING: ""
- MAX_RESPONSE_MS: 3000

## Payload structure
- valid_payload(): {"email": VALID_EMAIL, "password": VALID_PASSWORD, "resource": "admin"}
- wrong_password_payload(): same but with wrong password
- missing_resource_payload(): no "resource" key
- wrong_resource_payload(): resource="invalid_resource"
