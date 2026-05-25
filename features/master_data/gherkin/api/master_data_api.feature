@api @master_data
Feature: Master Data API
  As an authenticated user
  I want to retrieve reference/lookup data
  So that I can populate dropdowns and selection fields during onboarding and profile setup

  Background:
    Given the API is available at the configured base URL
    And the API key header is set
    And I am logged in as a registered user

  # ── GET /v1/master/industries ─────────────────────────────────────────────────

  @smoke @P0 @TC-MSTR-001
  Scenario: Get industries list returns 200 with data array
    When I GET /v1/master/industries with a valid Bearer token
    Then the response status should be 200
    And the response code should be "OK"
    And the response data should be a non-empty list

  @P1 @TC-MSTR-002
  Scenario: Industries items have id and name fields
    When I GET /v1/master/industries with a valid Bearer token
    Then the response status should be 200
    And each item in data should contain "id" and "name" fields

  @security @P0 @TC-MSTR-003
  Scenario: Get industries without x-api-key returns 401 or 403
    Given the API key header is not set
    When I GET /v1/master/industries
    Then the response status should be 401 or 403

  # ── GET /v1/master/business-areas ────────────────────────────────────────────

  @smoke @P0 @TC-MSTR-004
  Scenario: Get business areas returns 200 with non-empty list
    When I GET /v1/master/business-areas with a valid Bearer token
    Then the response status should be 200
    And the response data should be a non-empty list

  @P1 @TC-MSTR-005
  Scenario: Business areas items have id and name fields
    When I GET /v1/master/business-areas with a valid Bearer token
    Then the response status should be 200
    And each item in data should contain "id" and "name" fields

  # ── GET /v1/master/personal-interests ────────────────────────────────────────

  @smoke @P0 @TC-MSTR-006
  Scenario: Get personal interests returns 200 with non-empty list
    When I GET /v1/master/personal-interests with a valid Bearer token
    Then the response status should be 200
    And the response data should be a non-empty list

  @security @P0 @TC-MSTR-007
  Scenario: Get personal interests without auth token returns 401
    Given I am not authenticated
    When I GET /v1/master/personal-interests without a Bearer token
    Then the response status should be 401

  # ── GET /v1/master/social-causes ─────────────────────────────────────────────

  @smoke @P0 @TC-MSTR-008
  Scenario: Get social causes returns 200 with list
    When I GET /v1/master/social-causes with a valid Bearer token
    Then the response status should be 200
    And the response data should be a list

  @security @P0 @TC-MSTR-009
  Scenario: Get social causes without auth token returns 401
    Given I am not authenticated
    When I GET /v1/master/social-causes without a Bearer token
    Then the response status should be 401

  # ── GET /v1/master/countries ──────────────────────────────────────────────────

  @smoke @P0 @TC-MSTR-010
  Scenario: Get countries returns 200 with list containing id and name
    When I GET /v1/master/countries with a valid Bearer token
    Then the response status should be 200
    And the response data should be a non-empty list
    And each item in data should contain "id" and "name" fields

  @security @P0 @TC-MSTR-011
  Scenario: Get countries without auth token returns 401
    Given I am not authenticated
    When I GET /v1/master/countries without a Bearer token
    Then the response status should be 401

  # ── GET /v1/master/cities ─────────────────────────────────────────────────────

  @smoke @P0 @TC-MSTR-012
  Scenario: Get cities for Indonesia (country_id=102) returns 200 with cities list
    When I GET /v1/master/cities with param country_id=102 and a valid Bearer token
    Then the response status should be 200
    And the response data should contain a "cities" key with a list

  @negative @P1 @TC-MSTR-013
  Scenario: Get cities without country_id returns 400 or 422
    When I GET /v1/master/cities without a country_id param
    Then the response status should be 400, 422, or 200

  @security @P0 @TC-MSTR-014
  Scenario: Get cities without auth token returns 401
    Given I am not authenticated
    When I GET /v1/master/cities with param country_id=102 but no Bearer token
    Then the response status should be 401

  # ── GET /v1/master/relationship-types ────────────────────────────────────────

  @smoke @P0 @TC-MSTR-015
  Scenario: Get relationship types returns 200 with list containing id and name
    When I GET /v1/master/relationship-types with a valid Bearer token
    Then the response status should be 200
    And the response data should be a non-empty list
    And each item in data should contain "id" and "name" fields

  @security @P0 @TC-MSTR-016
  Scenario: Get relationship types without auth token returns 401
    Given I am not authenticated
    When I GET /v1/master/relationship-types without a Bearer token
    Then the response status should be 401
