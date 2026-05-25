@api @search
Feature: Search API
  As an authenticated user
  I want to search for posts and users and get typeahead suggestions
  So that I can discover relevant content and profiles

  Background:
    Given the API is available at the configured base URL
    And the API key header is set
    And I am logged in as a registered user

  # ── GET /v1/search/posts?tab=recent ──────────────────────────────────────────

  @smoke @P0 @TC-SRCH-001
  Scenario: Search posts with tab=recent returns 200
    When I GET /v1/search/posts with params query="hono", page=1, per_page=10, tab="recent"
    Then the response status should be 200
    And the response code should be "OK"
    And the response body should contain a "data" key

  @P1 @TC-SRCH-002
  Scenario: Search posts with no-match query returns empty list
    When I GET /v1/search/posts with params query="zzz_no_match_xqz", page=1, per_page=10, tab="recent"
    Then the response status should be 200
    And the response data should be a list

  @security @P0 @TC-SRCH-003
  Scenario: Search posts without auth token returns 401
    Given I am not authenticated
    When I GET /v1/search/posts with params query="hono", tab="recent" and no Bearer token
    Then the response status should be 401

  # ── GET /v1/search/posts?tab=top ─────────────────────────────────────────────

  @smoke @P0 @TC-SRCH-004
  Scenario: Search posts with tab=top returns 200
    When I GET /v1/search/posts with params query="hono", page=1, per_page=10, tab="top"
    Then the response status should be 200
    And the response code should be "OK"

  @negative @P1 @TC-SRCH-005
  Scenario: Search posts without query param returns 400 or 422
    When I GET /v1/search/posts with only param tab="recent" and no query param
    Then the response status should be 400, 422, or 200

  # ── GET /v1/search/typeahead ──────────────────────────────────────────────────

  @smoke @P0 @TC-SRCH-006
  Scenario: Typeahead with query returns 200 with suggestions
    When I GET /v1/search/typeahead with param query="ho"
    Then the response status should be 200
    And the response code should be "OK"

  @P1 @TC-SRCH-007
  Scenario: Typeahead response data is a dict or list
    When I GET /v1/search/typeahead with param query="ba"
    Then the response status should be 200
    And the response data should be a dict or list

  @security @P0 @TC-SRCH-008
  Scenario: Typeahead without auth token returns 401
    Given I am not authenticated
    When I GET /v1/search/typeahead with param query="test" and no Bearer token
    Then the response status should be 401

  # ── GET /v1/search/users ─────────────────────────────────────────────────────

  @smoke @P0 @TC-SRCH-009
  Scenario: Search users by query returns 200
    When I GET /v1/search/users with params query="test", page=1, per_page=10
    Then the response status should be 200
    And the response code should be "OK"
    And the response body should contain a "data" key

  @P1 @TC-SRCH-010
  Scenario: Search users with no-match query returns empty list
    When I GET /v1/search/users with params query="zzz_no_match_xqz999", page=1, per_page=10
    Then the response status should be 200
    And the response data should be a list

  @security @P0 @TC-SRCH-011
  Scenario: Search users without auth token returns 401
    Given I am not authenticated
    When I GET /v1/search/users with param query="test" and no Bearer token
    Then the response status should be 401
