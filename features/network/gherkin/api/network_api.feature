@api @network
Feature: Network API
  As an authenticated user
  I want to view my followers, following, and suggested connections
  So that I can manage and grow my professional network

  Background:
    Given the API is available at the configured base URL
    And the API key header is set

  # ── GET /v1/network/followers ─────────────────────────────────────────────────

  @smoke @P0 @TC-NET-001
  Scenario: Get followers returns 200 with data array
    Given I am logged in as a registered user
    When I GET /v1/network/followers with a valid Bearer token
    Then the response status should be 200
    And the response code should be "OK"
    And the response data should be a list

  @P1 @TC-NET-002
  Scenario: Get followers with pagination params returns 200
    Given I am logged in as a registered user
    When I GET /v1/network/followers with params page=1 and limit=10
    Then the response status should be 200

  @security @P0 @TC-NET-003
  Scenario: Get followers without auth token returns 401
    Given I am not authenticated
    When I GET /v1/network/followers without a Bearer token
    Then the response status should be 401

  # ── GET /v1/network/following ─────────────────────────────────────────────────

  @smoke @P0 @TC-NET-004
  Scenario: Get following returns 200 with data array
    Given I am logged in as a registered user
    When I GET /v1/network/following with a valid Bearer token
    Then the response status should be 200
    And the response code should be "OK"
    And the response data should be a list

  @P1 @TC-NET-005
  Scenario: Get following with search query param returns 200
    Given I am logged in as a registered user
    When I GET /v1/network/following with params page=1, limit=10, query="test"
    Then the response status should be 200

  @security @P0 @TC-NET-006
  Scenario: Get following without auth token returns 401
    Given I am not authenticated
    When I GET /v1/network/following without a Bearer token
    Then the response status should be 401

  # ── GET /v1/network/suggestions ───────────────────────────────────────────────

  @smoke @P0 @TC-NET-007
  Scenario: Get network suggestions returns 200
    Given I am logged in as a registered user
    When I GET /v1/network/suggestions with params page=1 and limit=10
    Then the response status should be 200
    And the response code should be "OK"

  @P1 @TC-NET-008
  Scenario: Suggestions data items have expected shape
    Given I am logged in as a registered user
    When I GET /v1/network/suggestions with params page=1 and limit=5
    Then the response status should be 200
    And each item in data should contain "id" or "creator" field

  @security @P0 @TC-NET-009
  Scenario: Get suggestions without auth token returns 401
    Given I am not authenticated
    When I GET /v1/network/suggestions without a Bearer token
    Then the response status should be 401
