@api @user_relationships
Feature: User Relationships API
  As an authenticated user
  I want to follow other users on the Hono platform
  So that I can build my network and see their content in my feed

  Background:
    Given the API is available at the configured base URL
    And the API key header is set

  # ── POST /v1/users/:id/follow ─────────────────────────────────────────────────

  @smoke @P0 @TC-UR-001
  Scenario: Follow a user returns 200 or 201
    Given I am logged in with valid credentials
    And a target user exists
    When I follow the target user with an optional relationship_type_id
    Then the response status should be 200 or 201

  @smoke @P0 @TC-UR-002
  Scenario: Re-following a user returns 200 (idempotent) or 409 (conflict)
    Given I am logged in with valid credentials
    And I have already followed the target user
    When I follow the same target user again
    Then the response status should be 200 or 409

  @negative @P1 @TC-UR-003
  Scenario: Following own user_id returns 400
    Given I am logged in with valid credentials
    When I try to follow my own user_id
    Then the response status should be 400

  @negative @P1 @TC-UR-004
  Scenario: Follow with non-existent user_id returns 404
    Given I am logged in with valid credentials
    When I follow user "00000000-0000-0000-0000-000000000000"
    Then the response status should be 404

  @negative @P1 @TC-UR-005
  Scenario: Follow with non-UUID path param returns 422
    Given I am logged in with valid credentials
    When I follow user "not-a-valid-uuid"
    Then the response status should be 422

  @negative @P0 @TC-UR-006
  Scenario: Follow without auth token returns 401
    Given the auth token is not set
    When I follow a target user
    Then the response status should be 401
