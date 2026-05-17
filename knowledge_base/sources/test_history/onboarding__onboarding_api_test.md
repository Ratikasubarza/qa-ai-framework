# Test file: features/onboarding/steps/api/onboarding_api_test.py

Suite: Onboarding API | Endpoint: PUT /v1/users/onboarding
Tests: TC-ONB-API-001 through TC-ONB-API-028 (28 tests)
Requires: authenticated user (Bearer token), approved_user fixture (DB-created)

## Test IDs covered
- TC-ONB-API-001 | Smoke | Complete onboarding valid data → 200 + DB onboarding_completed_at set
- TC-ONB-API-002 | Security | No token → 401
- TC-ONB-API-003 | Security | Invalid token → 401
- TC-ONB-API-004 | Boundary | Missing full_name → [DEV-BUG] returns 200 instead of 400
- TC-ONB-API-005 | Boundary | Missing city_id → [DEV-BUG] returns 200 instead of 400
- TC-ONB-API-006 | Negative | Invalid city_id=999999999 → [DEV-BUG] returns 500 with FK error
- TC-ONB-API-007 | Boundary | 3 industries (over max=2) → [DEV-BUG?] may return 200
- TC-ONB-API-008 | Boundary | Empty arrays for all ids → 200 or 400
- TC-ONB-API-009 | Negative | Non-existent industry IDs → [DEV-BUG] may return 500
- TC-ONB-API-010 | Boundary | Onboarding twice → first 200, second 400/422 (already onboarded)
- TC-ONB-API-011 | Boundary | Empty body → [DEV-BUG] returns 200 instead of 400
- TC-ONB-API-012 | Performance | Under 3s (Timeouts.API_SLA_MS)
- TC-ONB-API-013 | Boundary | industry_ids min 1 → should pass (200)
- TC-ONB-API-014 | Boundary | industry_ids max 2 → should pass (200)
- TC-ONB-API-015 | Boundary | industry_ids 3 (over max) → [DEV-BUG] if 200
- TC-ONB-API-016 | Boundary | industry_ids empty [] → [DEV-BUG] if 200
- TC-ONB-API-017 | Boundary | business_area_ids min 2 → should pass (200)
- TC-ONB-API-018 | Boundary | business_area_ids max 5 → should pass (200)
- TC-ONB-API-019 | Boundary | business_area_ids 6 (over max) → [DEV-BUG] if 200
- TC-ONB-API-020 | Boundary | business_area_ids 1 (below min=2) → [DEV-BUG] if 200
- TC-ONB-API-021 | Boundary | personal_interest_ids min 2 → should pass (200)
- TC-ONB-API-022 | Boundary | personal_interest_ids max 5 → should pass (200)
- TC-ONB-API-023 | Boundary | personal_interest_ids 6 (over max) → [DEV-BUG] if 200
- TC-ONB-API-024 | Boundary | personal_interest_ids 1 (below min=2) → [DEV-BUG] if 200
- TC-ONB-API-025 | Boundary | social_cause_ids min 2 → should pass (200)
- TC-ONB-API-026 | Boundary | social_cause_ids max 5 → should pass (200)
- TC-ONB-API-027 | Boundary | social_cause_ids 6 (over max) → [DEV-BUG] if 200
- TC-ONB-API-028 | Boundary | social_cause_ids 1 (below min=2) → [DEV-BUG] if 200

## Known DEV-BUGs in this suite
1. Missing full_name not validated — API returns 200 instead of 400
2. Missing city_id not validated — API returns 200 instead of 400
3. Invalid city_id returns 500 with raw DB FK error instead of 400/422
4. Possible: over-max industry/business_area/interest/cause IDs accepted silently

## Fixture
- approved_user: create_approved_user_sync(suffix=...) via core.db.test_user_helper
- get_user_token(email, password): logs in and returns accessToken
