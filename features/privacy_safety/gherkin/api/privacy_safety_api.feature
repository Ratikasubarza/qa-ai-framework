@api @privacy_safety
Feature: Privacy Safety API
  As an authenticated user
  I want to block, unblock, mute, and unmute other users
  So that I can control who can interact with me on the Hono platform

  Background:
    Given the API is available at the configured base URL
    And the API key header is set

  # ── POST /v1/settings/accounts/block ─────────────────────────────────────────

  @smoke @P0 @TC-PS-001
  Scenario: Block a single user returns 200 with OK code
    Given I am logged in with valid credentials
    And a target user exists
    When I block the target user
    Then the response status should be 200
    And the response code should be "OK"

  @smoke @P0 @TC-PS-002
  Scenario: Block 2 users in a single bulk request returns 200
    Given I am logged in with valid credentials
    And 2 target users exist
    When I block all target users in one request
    Then the response status should be 200

  @negative @P1 @TC-PS-003
  Scenario: Re-blocking an already-blocked user returns 200 or 422
    Given I am logged in with valid credentials
    And a target user is already blocked
    When I block the same target user again
    Then the response status should be 200 or 422

  @negative @P1 @TC-PS-004
  Scenario: Blocking own user_id returns 400
    Given I am logged in with valid credentials
    When I try to block my own user_id
    Then the response status should be 400

  @negative @P1 @TC-PS-005
  Scenario: Blocking a non-existent UUID returns 404
    Given I am logged in with valid credentials
    When I block user "00000000-0000-0000-0000-000000000000"
    Then the response status should be 404

  @negative @P1 @TC-PS-006
  Scenario: Block request with missing target_user_ids field returns 422
    Given I am logged in with valid credentials
    When I send a block request with an empty body
    Then the response status should be 422

  @negative @P1 @TC-PS-007
  Scenario: Block request with empty target_user_ids array returns 422
    Given I am logged in with valid credentials
    When I send a block request with an empty target_user_ids array
    Then the response status should be 422

  @security @P0 @TC-PS-008
  Scenario: Block request without auth token returns 401
    Given the auth token is not set
    When I send a block request
    Then the response status should be 401

  # ── DELETE /v1/settings/accounts/block ───────────────────────────────────────

  @smoke @P0 @TC-PS-009
  Scenario: Unblock a single user returns 200
    Given I am logged in with valid credentials
    And a target user is currently blocked
    When I unblock the target user
    Then the response status should be 200

  @smoke @P0 @TC-PS-010
  Scenario: Unblock 2 users in bulk returns 200
    Given I am logged in with valid credentials
    And 2 target users are currently blocked
    When I unblock all target users in one request
    Then the response status should be 200

  @negative @P1 @TC-PS-011
  Scenario: Unblocking a user who is not blocked returns 200 or 404
    Given I am logged in with valid credentials
    And the target user is not blocked
    When I unblock the target user
    Then the response status should be 200 or 404

  @negative @P1 @TC-PS-012
  Scenario: Unblock request with empty array returns 422
    Given I am logged in with valid credentials
    When I send an unblock request with an empty target_user_ids array
    Then the response status should be 422

  @security @P0 @TC-PS-013
  Scenario: Unblock request without auth token returns 401
    Given the auth token is not set
    When I send an unblock request
    Then the response status should be 401

  # ── POST /v1/settings/accounts/mute ──────────────────────────────────────────

  @smoke @P0 @TC-PS-014
  Scenario: Mute a single user returns 200 with OK code
    Given I am logged in with valid credentials
    And a target user exists
    When I mute the target user
    Then the response status should be 200
    And the response code should be "OK"

  @smoke @P0 @TC-PS-015
  Scenario: Mute 2 users in a single bulk request returns 200
    Given I am logged in with valid credentials
    And 2 target users exist
    When I mute all target users in one request
    Then the response status should be 200

  @negative @P1 @TC-PS-016
  Scenario: Re-muting an already-muted user returns 200 or 422
    Given I am logged in with valid credentials
    And a target user is already muted
    When I mute the same target user again
    Then the response status should be 200 or 422

  @negative @P1 @TC-PS-017
  Scenario: Muting a non-existent UUID returns 404
    Given I am logged in with valid credentials
    When I mute user "00000000-0000-0000-0000-000000000000"
    Then the response status should be 404

  @negative @P1 @TC-PS-018
  Scenario: Mute request with missing target_user_ids field returns 422
    Given I am logged in with valid credentials
    When I send a mute request with an empty body
    Then the response status should be 422

  @security @P0 @TC-PS-019
  Scenario: Mute request without auth token returns 401
    Given the auth token is not set
    When I send a mute request
    Then the response status should be 401

  # ── DELETE /v1/settings/accounts/mute ────────────────────────────────────────

  @smoke @P0 @TC-PS-020
  Scenario: Unmute a single user returns 200
    Given I am logged in with valid credentials
    And a target user is currently muted
    When I unmute the target user
    Then the response status should be 200

  @smoke @P0 @TC-PS-021
  Scenario: Unmute 2 users in bulk returns 200
    Given I am logged in with valid credentials
    And 2 target users are currently muted
    When I unmute all target users in one request
    Then the response status should be 200

  @negative @P1 @TC-PS-022
  Scenario: Unmuting a user who is not muted returns 200 or 404
    Given I am logged in with valid credentials
    And the target user is not muted
    When I unmute the target user
    Then the response status should be 200 or 404

  @security @P0 @TC-PS-023
  Scenario: Unmute request without auth token returns 401
    Given the auth token is not set
    When I send an unmute request
    Then the response status should be 401

  # ── GET /v1/settings/account/list?section=BLOCKED ────────────────────────────

  @smoke @P0 @TC-PS-024
  Scenario: Get blocked list returns 200 with at least one entry and valid schema
    Given I am logged in with valid credentials
    And I have blocked at least one target user
    When I request the blocked users list
    Then the response status should be 200
    And the response code should be "OK"
    And the list should contain at least 1 entry
    And each entry should contain fields "id", "name", "is_verified"

  @smoke @P0 @TC-PS-025
  Scenario: Blocked list is empty after all target users are unblocked
    Given I am logged in with valid credentials
    And all target users have been unblocked
    When I request the blocked users list
    Then the response status should be 200
    And the list should be empty

  @P1 @TC-PS-026
  Scenario: Blocked list with q= search param returns 200
    Given I am logged in with valid credentials
    And I have blocked at least one target user
    When I request the blocked users list with search query "a"
    Then the response status should be 200

  @boundary @P2 @TC-PS-027
  Scenario: Blocked list with pagination params returns 200
    Given I am logged in with valid credentials
    When I request the blocked users list with page 1 and per_page 5
    Then the response status should be 200

  @negative @P1 @TC-PS-028
  Scenario: Account list with invalid section returns 422
    Given I am logged in with valid credentials
    When I request the account list with section "INVALID_SECTION"
    Then the response status should be 422

  @security @P0 @TC-PS-029
  Scenario: Get blocked list without auth token returns 401
    Given the auth token is not set
    When I request the blocked users list
    Then the response status should be 401

  # ── GET /v1/settings/account/list?section=MUTED ──────────────────────────────

  @smoke @P0 @TC-PS-030
  Scenario: Get muted list returns 200 with at least one entry
    Given I am logged in with valid credentials
    And I have muted at least one target user
    When I request the muted users list
    Then the response status should be 200
    And the response code should be "OK"
    And the list should contain at least 1 entry

  @smoke @P0 @TC-PS-031
  Scenario: Muted list is empty after all target users are unmuted
    Given I am logged in with valid credentials
    And all target users have been unmuted
    When I request the muted users list
    Then the response status should be 200
    And the list should be empty

  @P1 @TC-PS-032
  Scenario: Muted list with q= search param returns 200
    Given I am logged in with valid credentials
    And I have muted at least one target user
    When I request the muted users list with search query "a"
    Then the response status should be 200

  @security @P0 @TC-PS-033
  Scenario: Get muted list without auth token returns 401
    Given the auth token is not set
    When I request the muted users list
    Then the response status should be 401
