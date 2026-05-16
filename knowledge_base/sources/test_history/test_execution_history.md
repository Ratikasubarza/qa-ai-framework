# Hono App — Test Execution History

## API Test Suite — Summary (as of May 2026)

### Total Tests
- **Total**: ~199 tests across all suites
- **API Tests**: ~130 tests
- **Mobile Tests**: ~13 tests
- **Pipeline/Agent Tests**: ~56 tests

### Pass/Fail/Skip Rates (API suite)
- **Passed**: ~71 per run (stable environment)
- **Skipped**: ~31 per run (Resend quota exhausted — expected, not a failure)
- **Failed**: 0 (when Resend quota available)

### Known Flaky Tests
- **test_TC_CMS_APPROVE_001** — depends on register, flaky when Resend quota exhausted
- **test_TC_CMS_REJECT_001 to 010** — same dependency
- **test_TC_REG_API_001** — depends on Resend quota

### Stable High-Value Tests
- test_TC_API_001 — login smoke (always stable)
- test_TC_API_002 — wrong password (always stable)
- test_TC_CMS_API_001 — CMS login (always stable)
- test_TC_USERS_ACCOUNT_001 — get account (depends on DB user creation)
- test_TC_USERS_PASSWORD_001 — password change E2E (requires DB write)

### Test Categories Coverage
| Category        | Count | Coverage |
|----------------|-------|----------|
| Smoke          | 12    | ✅        |
| Security       | 18    | ✅        |
| Negative       | 35    | ✅        |
| Boundary       | 28    | ✅        |
| Performance    | 6     | ✅        |
| Functional/E2E | 30    | ✅        |

### xfail Tests (Known Product Bugs)
- test_TC_USERS_EMAIL_004 — verify-email 404 (DEV-BUG-001)
- test_TC_USERS_EMAIL_005 — verify-email expired code (DEV-BUG-001)
- test_TC_USERS_ACCOUNT_003 — nationality field missing (DEV-BUG-002)

### CI/CD Integration
- GitHub Actions: pytest runs on push to main
- JUnit XML output: reports/junit/results.xml
- Allure report: reports/allure/report/
- Allure results: reports/allure/results/

### Test Data Strategy
- Synthetic users created via DB helpers (create_approved_user)
- TEST_USER_PASSWORD from .env — single source of truth
- Register tests use unique timestamps for email/phone uniqueness
- DB reset in teardown for password/email change tests
