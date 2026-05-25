@api @public
Feature: Public API
  As any client (no authentication required)
  I want to retrieve country and city reference data
  So that I can populate location fields during registration without needing a login

  Background:
    Given the API is available at the configured base URL
    And the API key header is set

  # ── GET /v1/public/countries ──────────────────────────────────────────────────

  @smoke @P0 @TC-PUB-001
  Scenario: List countries returns 200 without auth token
    Given I am not authenticated
    When I GET /v1/public/countries without a Bearer token
    Then the response status should be 200
    And the response code should be "OK"
    And the response data should be a non-empty list

  @P1 @TC-PUB-002
  Scenario: Countries items have id and name fields
    Given I am not authenticated
    When I GET /v1/public/countries
    Then the response status should be 200
    And each item in data should contain "id" and "name" fields

  @P2 @TC-PUB-003
  Scenario: Public countries endpoint responds within 3000ms
    Given I am not authenticated
    When I GET /v1/public/countries
    Then the response status should be 200
    And the response time should be under 3000ms

  # ── GET /v1/public/cities ─────────────────────────────────────────────────────

  @smoke @P0 @TC-PUB-004
  Scenario: List cities for Indonesia returns 200 without auth
    Given I am not authenticated
    When I GET /v1/public/cities with param country_id=102 without a Bearer token
    Then the response status should be 200
    And the response code should be "OK"
    And the response data should contain a "cities" key or be a list

  @P1 @TC-PUB-005
  Scenario: Cities response includes cities list
    Given I am not authenticated
    When I GET /v1/public/cities with param country_id=102
    Then the response status should be 200
    And the response data should contain a list of cities

  @negative @P1 @TC-PUB-006
  Scenario: Get cities without country_id returns 400 or empty result
    Given I am not authenticated
    When I GET /v1/public/cities without a country_id param
    Then the response status should be 400, 422, or 200
