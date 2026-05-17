# Test file: features/register/steps/api/register_api_test.py

Suite: Register API | Endpoint: POST /v1/users/register
Tests: TC-REG-API-001 through TC-REG-API-030 (30 tests)
Marks: smoke, sanity, security, boundary, combination, performance, negative, api

## Test IDs covered
- TC-REG-API-001 | Smoke | Register with valid data returns OK (200)
- TC-REG-API-002 | Negative | Duplicate email returns 4xx
- TC-REG-API-003 | Boundary | Missing required fields returns 400/422
- TC-REG-API-004 | Negative | Invalid email format returns 400/422
- TC-REG-API-005 | Boundary | Empty body returns 400/422
- TC-REG-API-006 | Negative | Duplicate email (KnownAccounts.EXISTING_EMAIL_A) returns 4xx
- TC-REG-API-007 | Negative | Duplicate phone (KnownAccounts.EXISTING_PHONE_A) returns 4xx
- TC-REG-API-008 | Combination | Duplicate email + valid phone → blocked
- TC-REG-API-009 | Combination | Valid email + duplicate phone → blocked
- TC-REG-API-010 | Negative | Invalid email formats: notanemail, missing@, @nodomain, spaces in@email
- TC-REG-API-011 | Negative | Non-numeric phone returns 400/422
- TC-REG-API-012 | Security | Missing x-api-key returns 401/403
- TC-REG-API-013 | Security | SQL injection in fullname handled safely
- TC-REG-API-014 | Boundary | Very long fullname (501 chars = BoundaryValues.LONG_NAME_LENGTH)
- TC-REG-API-015 | Combination | Both email AND phone duplicate → blocked
- TC-REG-API-016 | Boundary | Minimum valid data returns 200
- TC-REG-API-017 | Boundary | Special chars in fullname → 200 or 400
- TC-REG-API-018 | Negative | Missing fullname field returns 400/422
- TC-REG-API-019 | Negative | Missing linkedin field → documents API behavior
- TC-REG-API-020 | Negative | Invalid phone_country_code "XX" returns 400/422
- TC-REG-API-021 | Boundary | Phone number "123" (too short) returns 400/422
- TC-REG-API-022 | Boundary | 21-digit phone number → documents behavior
- TC-REG-API-023 | Security | XSS payload in fullname handled safely
- TC-REG-API-024 | Boundary | Valid LinkedIn URL accepted (200)
- TC-REG-API-025 | Negative | Invalid LinkedIn URL → documents behavior
- TC-REG-API-026 | Performance | Register response time under 3s
- TC-REG-API-027 | Boundary | Empty string fullname returns 400/422
- TC-REG-API-028 | Boundary | Whitespace-only fullname → documents behavior
- TC-REG-API-029 | Combination | Register same user twice → second blocked
- TC-REG-API-030 | Combination | Null values in email/fullname returns 400/422

## Key test data
- KnownAccounts.EXISTING_EMAIL_A — already registered email A
- KnownAccounts.EXISTING_PHONE_A — already registered phone A (HonoA)
- KnownAccounts.EXISTING_PHONE_B — already registered phone B (HonoB)
- BoundaryValues.LONG_NAME_LENGTH = 501 chars
- RegisterTestData.valid_payload() — unique timestamped payload
- RegisterTestData.INVALID_EMAIL_PAYLOAD, MISSING_FIELDS_PAYLOAD, EMPTY_PAYLOAD

## skip_on_email_quota
Tests that actually register users skip if Resend daily email quota is reached.
