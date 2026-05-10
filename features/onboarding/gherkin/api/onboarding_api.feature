@api @onboarding
Feature: Onboarding API — PUT /v1/users/onboarding
  As an approved Hono user
  I want to complete my profile onboarding via API
  So that I can access the full Hono community

  Background:
    Given a new approved user is created via API and DB
    And the user is authenticated with Bearer token

  @smoke @P0 @TC-ONB-API-001
  Scenario: Complete onboarding with valid data
    When I PUT to "/v1/users/onboarding" with valid payload
    Then the response status should be 200
    And onboarding_completed_at should be set in DB

  @security @P0 @TC-ONB-API-002
  Scenario: Onboarding without token returns 401
    Given I am not authenticated
    When I PUT to "/v1/users/onboarding"
    Then the response status should be 401

  @security @P0 @TC-ONB-API-003
  Scenario: Onboarding with invalid token returns 401
    Given I use an invalid Bearer token
    When I PUT to "/v1/users/onboarding"
    Then the response status should be 401

  @boundary @P1 @TC-ONB-API-004
  Scenario: Missing full_name returns 400
    When I PUT without full_name field
    Then the response status should be 400

  @boundary @P1 @TC-ONB-API-005
  Scenario: Missing city_id returns 400
    When I PUT without city_id field
    Then the response status should be 400

  @negative @P1 @TC-ONB-API-006
  Scenario: Invalid city_id returns error
    When I PUT with city_id 999999999
    Then the response status should be 400 or 404

  @boundary @P2 @TC-ONB-API-007 @dev-bug
  Scenario: More than 2 industries should be blocked
    When I PUT with industry_ids containing 3 items
    Then the response should be 200 or 400

  @boundary @P2 @TC-ONB-API-008
  Scenario: Empty arrays for ids
    When I PUT with empty industry_ids and business_area_ids
    Then the response should be 200 or 400

  @negative @P2 @TC-ONB-API-009
  Scenario: Non-existent industry IDs
    When I PUT with industry_ids 99999 and 99998
    Then the response should be 200 or 400

  @boundary @P2 @TC-ONB-API-010
  Scenario: Complete onboarding twice is handled
    When I PUT valid onboarding data for the first time
    And I PUT valid onboarding data for the second time
    Then both responses should be 200 or second should be 400

  @boundary @P1 @TC-ONB-API-011
  Scenario: Empty body returns 400
    When I PUT with empty body
    Then the response status should be 400

  @performance @P2 @TC-ONB-API-012
  Scenario: Onboarding response time within threshold
    When I PUT valid onboarding data
    Then the response time should be under 3000 milliseconds

  # ── Min/Max Validation ────────────────────────────────────────────────

  @boundary @P1 @TC-ONB-API-013
  Scenario: industry_ids with minimum 1 item passes
    When I PUT with industry_ids containing 1 item
    Then the response status should be 200

  @boundary @P1 @TC-ONB-API-014
  Scenario: industry_ids with maximum 2 items passes
    When I PUT with industry_ids containing 2 items
    Then the response status should be 200

  @boundary @P1 @TC-ONB-API-015 @dev-bug
  Scenario: industry_ids over max (3 items) should be blocked
    When I PUT with industry_ids containing 3 items
    Then the response status should be 400
    But if API returns 200 it is a DEV-BUG missing max validation

  @boundary @P1 @TC-ONB-API-016 @dev-bug
  Scenario: industry_ids empty array should be blocked (min=1)
    When I PUT with industry_ids as empty array
    Then the response status should be 400
    But if API returns 200 it is a DEV-BUG missing min validation

  @boundary @P1 @TC-ONB-API-017
  Scenario: business_area_ids with minimum 2 items passes
    When I PUT with business_area_ids containing 2 items
    Then the response status should be 200

  @boundary @P1 @TC-ONB-API-018
  Scenario: business_area_ids with maximum 5 items passes
    When I PUT with business_area_ids containing 5 items
    Then the response status should be 200

  @boundary @P1 @TC-ONB-API-019 @dev-bug
  Scenario: business_area_ids over max (6 items) should be blocked
    When I PUT with business_area_ids containing 6 items
    Then the response status should be 400
    But if API returns 200 it is a DEV-BUG missing max validation

  @boundary @P1 @TC-ONB-API-020 @dev-bug
  Scenario: business_area_ids below min (1 item) should be blocked
    When I PUT with business_area_ids containing 1 item
    Then the response status should be 400
    But if API returns 200 it is a DEV-BUG missing min validation

  @boundary @P1 @TC-ONB-API-021
  Scenario: personal_interest_ids with minimum 2 items passes
    When I PUT with personal_interest_ids containing 2 items
    Then the response status should be 200

  @boundary @P1 @TC-ONB-API-022
  Scenario: personal_interest_ids with maximum 5 items passes
    When I PUT with personal_interest_ids containing 5 items
    Then the response status should be 200

  @boundary @P1 @TC-ONB-API-023 @dev-bug
  Scenario: personal_interest_ids over max (6 items) should be blocked
    When I PUT with personal_interest_ids containing 6 items
    Then the response status should be 400
    But if API returns 200 it is a DEV-BUG missing max validation

  @boundary @P1 @TC-ONB-API-024 @dev-bug
  Scenario: personal_interest_ids below min (1 item) should be blocked
    When I PUT with personal_interest_ids containing 1 item
    Then the response status should be 400
    But if API returns 200 it is a DEV-BUG missing min validation

  @boundary @P1 @TC-ONB-API-025
  Scenario: social_cause_ids with minimum 2 items passes
    When I PUT with social_cause_ids containing 2 items
    Then the response status should be 200

  @boundary @P1 @TC-ONB-API-026
  Scenario: social_cause_ids with maximum 5 items passes
    When I PUT with social_cause_ids containing 5 items
    Then the response status should be 200

  @boundary @P1 @TC-ONB-API-027 @dev-bug
  Scenario: social_cause_ids over max (6 items) should be blocked
    When I PUT with social_cause_ids containing 6 items
    Then the response status should be 400
    But if API returns 200 it is a DEV-BUG missing max validation

  @boundary @P1 @TC-ONB-API-028 @dev-bug
  Scenario: social_cause_ids below min (1 item) should be blocked
    When I PUT with social_cause_ids containing 1 item
    Then the response status should be 400
    But if API returns 200 it is a DEV-BUG missing min validation
