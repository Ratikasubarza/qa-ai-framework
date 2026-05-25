@api @privacy
Feature: Privacy API
  As an authenticated user
  I want to follow, unfollow, block, unblock, mute, and unmute other users
  And view my blocked and muted account lists and counts
  So that I can control who interacts with my content

  Background:
    Given the API is available at the configured base URL
    And the API key header is set

  # ── POST /v1/users/:id/follow ─────────────────────────────────────────────────

  @smoke @P0 @TC-PRIV-001
  Scenario: Follow a valid user returns 200
    Given I am logged in as an actor user
    And a valid target user exists
    When I POST to /v1/users/:target_id/follow with relationship_type_id ""
    Then the response status should be 200 or 201

  @security @P0 @TC-PRIV-002
  Scenario: Follow a user without auth returns 401
    Given I am not authenticated
    When I POST to /v1/users/:target_id/follow with relationship_type_id ""
    Then the response status should be 401

  @negative @P1 @TC-PRIV-003
  Scenario: Follow a non-existent user returns 404
    Given I am logged in as an actor user
    And the target user id is "00000000-0000-0000-0000-000000000000"
    When I POST to /v1/users/:target_id/follow with relationship_type_id ""
    Then the response status should be 400 or 404

  # ── DELETE /v1/users/:id/follow ───────────────────────────────────────────────

  @smoke @P0 @TC-PRIV-004
  Scenario: Unfollow a user returns 200
    Given I am logged in as an actor user
    And I am following the target user
    When I DELETE /v1/users/:target_id/follow
    Then the response status should be 200, 204, or 404

  @security @P0 @TC-PRIV-005
  Scenario: Unfollow a user without auth returns 401
    Given I am not authenticated
    When I DELETE /v1/users/:target_id/follow without a Bearer token
    Then the response status should be 401

  # ── POST /v1/settings/accounts/block ─────────────────────────────────────────

  @smoke @P0 @TC-PRIV-006
  Scenario: Block a user returns 200
    Given I am logged in as an actor user
    And a valid target user exists
    When I POST to /v1/settings/accounts/block with target_user_ids containing the target id
    Then the response status should be 200 or 201

  @security @P0 @TC-PRIV-007
  Scenario: Block a user without auth returns 401
    Given I am not authenticated
    When I POST to /v1/settings/accounts/block with any target_user_ids
    Then the response status should be 401

  @negative @P1 @TC-PRIV-008
  Scenario: Block with empty target_user_ids list returns 400 or 422
    Given I am logged in as an actor user
    When I POST to /v1/settings/accounts/block with target_user_ids as an empty array
    Then the response status should be 400, 422, or 200

  # ── DELETE /v1/settings/accounts/block ───────────────────────────────────────

  @smoke @P0 @TC-PRIV-009
  Scenario: Unblock a previously blocked user returns 200
    Given I am logged in as an actor user
    And the target user is currently blocked
    When I DELETE /v1/settings/accounts/block with target_user_ids containing the target id
    Then the response status should be 200 or 204

  @security @P0 @TC-PRIV-010
  Scenario: Unblock without auth returns 401
    Given I am not authenticated
    When I DELETE /v1/settings/accounts/block with any target_user_ids
    Then the response status should be 401

  # ── POST /v1/settings/accounts/mute ──────────────────────────────────────────

  @smoke @P0 @TC-PRIV-011
  Scenario: Mute a user returns 200
    Given I am logged in as an actor user
    And a valid target user exists
    When I POST to /v1/settings/accounts/mute with target_user_ids containing the target id
    Then the response status should be 200 or 201

  @security @P0 @TC-PRIV-012
  Scenario: Mute a user without auth returns 401
    Given I am not authenticated
    When I POST to /v1/settings/accounts/mute with any target_user_ids
    Then the response status should be 401

  # ── DELETE /v1/settings/accounts/mute ────────────────────────────────────────

  @smoke @P0 @TC-PRIV-013
  Scenario: Unmute a user returns 200
    Given I am logged in as an actor user
    And the target user is currently muted
    When I DELETE /v1/settings/accounts/mute with target_user_ids containing the target id
    Then the response status should be 200 or 204

  @security @P0 @TC-PRIV-014
  Scenario: Unmute without auth returns 401
    Given I am not authenticated
    When I DELETE /v1/settings/accounts/mute with any target_user_ids
    Then the response status should be 401

  # ── POST /v1/users/:user_id/mute ─────────────────────────────────────────────

  @smoke @P0 @TC-PRIV-015
  Scenario: Mute user via profile endpoint returns 200
    Given I am logged in as an actor user
    And a valid target user exists
    When I POST to /v1/users/:target_id/mute
    Then the response status should be 200 or 201

  @negative @P1 @TC-PRIV-016
  Scenario: Mute yourself returns 400
    Given I am logged in as an actor user
    When I POST to /v1/users/:my_own_id/mute
    Then the response status should be 400 or 422

  # ── GET /v1/settings/account/counts ──────────────────────────────────────────

  @smoke @P0 @TC-PRIV-017
  Scenario: Get blocked and muted counts returns 200 with count fields
    Given I am logged in as an actor user
    When I GET /v1/settings/account/counts
    Then the response status should be 200
    And the response data should contain "blocked_count" and "muted_count"

  @security @P0 @TC-PRIV-018
  Scenario: Get counts without auth returns 401
    Given I am not authenticated
    When I GET /v1/settings/account/counts without a Bearer token
    Then the response status should be 401

  # ── GET /v1/settings/account/list ────────────────────────────────────────────

  @smoke @P0 @TC-PRIV-019
  Scenario: Get blocked users list returns 200 with items
    Given I am logged in as an actor user
    When I GET /v1/settings/account/list with params section="BLOCKED", page=1, per_page=20
    Then the response status should be 200
    And the response data should contain an "items" key

  @security @P0 @TC-PRIV-020
  Scenario: Get blocked list without auth returns 401
    Given I am not authenticated
    When I GET /v1/settings/account/list with params section="BLOCKED" but no Bearer token
    Then the response status should be 401

  @negative @P1 @TC-PRIV-021
  Scenario: Get account list with invalid section value returns 400 or 422
    Given I am logged in as an actor user
    When I GET /v1/settings/account/list with param section="INVALID_SECTION"
    Then the response status should be 400 or 422

  @smoke @P0 @TC-PRIV-022
  Scenario: Get muted users list returns 200 with items
    Given I am logged in as an actor user
    When I GET /v1/settings/account/list with params section="MUTED", page=1, per_page=20
    Then the response status should be 200
    And the response data should contain an "items" key
