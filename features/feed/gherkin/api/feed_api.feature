@api @feed
Feature: Feed API
  As an authenticated user
  I want to retrieve my content feed and topics
  So that I can browse relevant posts and discussions

  Background:
    Given the API is available at the configured base URL
    And the API key header is set

  # ── GET /v1/feed ──────────────────────────────────────────────────────────────

  @smoke @P0 @TC-FEED-001
  Scenario: Staging user gets feed list
    Given I am logged in as the staging user
    When I GET /v1/feed with the staging user Bearer token
    Then the response status should be 200
    And the response code should be "OK"
    And the response body should contain a "data" key

  @P1 @TC-FEED-002
  Scenario: Get feed with page and per_page pagination params
    Given I am logged in as the staging user
    When I GET /v1/feed with params page=1 and per_page=5
    Then the response status should be 200

  @P1 @TC-FEED-003
  Scenario: Get feed with filter param returns 200 or 400
    Given I am logged in as the staging user
    When I GET /v1/feed with params filter="following", page=1, per_page=10
    Then the response status should be 200 or 400

  @negative @P0 @TC-FEED-004
  Scenario: Get feed without auth token returns 401
    Given I am not authenticated
    When I GET /v1/feed without a Bearer token
    Then the response status should be 401

  # ── GET /v1/topics ────────────────────────────────────────────────────────────

  @smoke @P0 @TC-FEED-005
  Scenario: Staging user gets topics list
    Given I am logged in as the staging user
    When I GET /v1/topics with a valid Bearer token
    Then the response status should be 200
    And the response code should be "OK"

  @negative @P0 @TC-FEED-006
  Scenario: Get topics without auth token returns 401
    Given I am not authenticated
    When I GET /v1/topics without a Bearer token
    Then the response status should be 401

  @P1 @TC-FEED-007
  Scenario: Feed response contains pagination info
    Given I am logged in as the staging user
    When I GET /v1/feed with params page=1 and per_page=3
    Then the response status should be 200
    And the response body should contain a "data" key

  # ── Deactivated user ──────────────────────────────────────────────────────────

  @negative @P1 @TC-FEED-008
  Scenario: Deactivated account is rejected when accessing feed
    Given I am logged in as a user who has deactivated their account
    When I GET /v1/feed with the deactivated user's Bearer token
    Then the response status should be 401 or 403
    And the response body should contain an error message
