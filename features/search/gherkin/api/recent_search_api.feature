@api @search
Feature: Recent Search API
  As an authenticated user
  I want to manage my recent search history
  So that I can quickly revisit profiles I have searched for

  Background:
    Given the API is available at the configured base URL
    And the API key header is set

  # ── GET /v1/search/recent ────────────────────────────────────────────────────

  @smoke @P0 @TC-RS-001
  Scenario: Get recent searches returns list after adding an entry
    Given I am logged in with valid credentials
    And I have added a user profile to my recent searches
    When I request my recent search list
    Then the response status should be 200
    And the response code should be "OK"
    And the list should contain at least 1 entry
    And each entry should contain fields "id", "name", "role", "profile_picture_url", "is_verified"

  @smoke @P0 @TC-RS-002
  Scenario: Get recent searches returns empty list after clearing history
    Given I am logged in with valid credentials
    And I have cleared all my recent searches
    When I request my recent search list
    Then the response status should be 200
    And the list should be empty

  @smoke @P0 @TC-RS-003
  Scenario: Recent search response fields match expected types
    Given I am logged in with valid credentials
    And I have added a user profile to my recent searches
    When I request my recent search list
    Then the response status should be 200
    And the "id" field should be a string
    And the "name" field should be a string
    And the "role" field should be a string
    And the "is_verified" field should be a boolean
    And the "profile_picture_url" field should be a string or null

  @security @P0 @TC-RS-004
  Scenario: Get recent searches without x-api-key returns 401
    Given the API key header is not set
    When I request my recent search list
    Then the response status should be 401

  # ── POST /v1/search/recent ───────────────────────────────────────────────────

  @smoke @P0 @TC-RS-005
  Scenario: Add a user profile to recent searches successfully
    Given I am logged in with valid credentials
    And a target user exists
    When I add the target user to my recent searches
    Then the response status should be 200
    And the response code should be "OK"
    And the response message should contain "Data saved"

  @negative @P1 @TC-RS-006
  Scenario: Add recent search with missing user_id returns 422
    Given I am logged in with valid credentials
    When I add a recent search with an empty body
    Then the response status should be 422

  @negative @P1 @TC-RS-007
  Scenario: Add recent search with non-UUID user_id returns 422
    Given I am logged in with valid credentials
    When I add a recent search with user_id "not-a-valid-uuid"
    Then the response status should be 422

  @negative @P1 @TC-RS-008
  Scenario: Add recent search with non-existent user_id returns 404
    Given I am logged in with valid credentials
    When I add a recent search with user_id "00000000-0000-0000-0000-000000000000"
    Then the response status should be 404

  @boundary @P2 @TC-RS-009
  Scenario: Adding a 6th entry evicts the oldest entry (FIFO, max 5)
    Given I am logged in with valid credentials
    And my recent search history has been cleared
    And I have added 5 different user profiles to my recent searches
    When I add a 6th user profile to my recent searches
    Then the response status should be 200
    And the recent search list should contain exactly 5 entries
    And the oldest entry should have been evicted
    And the newest entry should be present in the list

  @security @P1 @TC-RS-010
  Scenario: Add recent search without x-api-key returns 401
    Given the API key header is not set
    When I add a user to my recent searches
    Then the response status should be 401

  # ── DELETE /v1/search/recent/{user_id} ───────────────────────────────────────

  @smoke @P0 @TC-RS-011
  Scenario: Delete a recent search entry successfully
    Given I am logged in with valid credentials
    And I have added a user profile to my recent searches
    When I delete that user from my recent searches
    Then the response status should be 200
    And the response code should be "OK"
    And the response message should contain "Data deleted"

  @negative @P1 @TC-RS-012
  Scenario: Delete a user not in recent searches returns 404
    Given I am logged in with valid credentials
    When I delete user "00000000-0000-0000-0000-000000000000" from my recent searches
    Then the response status should be 404

  @negative @P1 @TC-RS-013
  Scenario: Delete recent search with non-UUID user_id returns 422
    Given I am logged in with valid credentials
    When I delete user "not-a-uuid" from my recent searches
    Then the response status should be 422

  @security @P1 @TC-RS-014
  Scenario: Delete recent search without x-api-key returns 401
    Given the API key header is not set
    When I delete a user from my recent searches
    Then the response status should be 401
