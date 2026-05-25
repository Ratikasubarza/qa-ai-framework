@api @post_interactions
Feature: Post Interactions API
  As an authenticated user
  I want to report, mark not-interested, and track views on posts
  So that I can manage my content experience on the Hono platform

  Background:
    Given the API is available at the configured base URL
    And the API key header is set

  # ── Report Post ─────────────────────────────────────────────────────────────

  @smoke @P0 @TC-PI-001
  Scenario: Authenticated user reports another user's post
    Given I am logged in with valid credentials
    And a post exists that was created by another user
    When I report the post with reason "spam"
    Then the response status should be 200
    And the response code should be "OK"

  @security @P0 @TC-PI-002
  Scenario: Report post without Bearer token returns 401
    Given I am not authenticated
    When I report a post
    Then the response status should be 401

  @negative @P1 @TC-PI-003
  Scenario: Report non-existent post returns 404
    Given I am logged in with valid credentials
    When I report a post with id "00000000-0000-0000-0000-000000000000"
    Then the response status should be 404

  @negative @P1 @TC-PI-004
  Scenario: User cannot report their own post
    Given I am logged in with valid credentials
    And I have created a post
    When I report my own post
    Then the response status should be 400 or 403

  # ── Not Interested ───────────────────────────────────────────────────────────

  @smoke @P0 @TC-PI-005
  Scenario: Authenticated user marks a post as not interested
    Given I am logged in with valid credentials
    And a post exists that was created by another user
    When I mark the post as not interested
    Then the response status should be 200
    And the response code should be "OK"

  @security @P0 @TC-PI-006
  Scenario: Not-interested without Bearer token returns 401
    Given I am not authenticated
    When I mark a post as not interested
    Then the response status should be 401

  @negative @P1 @TC-PI-007
  Scenario: Not-interested on non-existent post returns 404
    Given I am logged in with valid credentials
    When I mark post "00000000-0000-0000-0000-000000000000" as not interested
    Then the response status should be 404

  @negative @P1 @TC-PI-008
  Scenario: Not-interested on admin-hidden post is rejected
    Given I am logged in with valid credentials
    And a post has been hidden by an admin
    When I mark the hidden post as not interested
    Then the response status should be 400, 403, or 404

  # ── Track View ───────────────────────────────────────────────────────────────

  @smoke @P0 @TC-PI-009
  Scenario: Authenticated user tracks a post view
    Given I am logged in with valid credentials
    And a post exists that was created by another user
    When I track a view on the post
    Then the response status should be 200

  @security @P0 @TC-PI-010
  Scenario: Track view without Bearer token returns 401
    Given I am not authenticated
    When I track a view on a post
    Then the response status should be 401

  @negative @P1 @TC-PI-011
  Scenario: Track view on non-existent post returns 404
    Given I am logged in with valid credentials
    When I track a view on post "00000000-0000-0000-0000-000000000000"
    Then the response status should be 404

  @boundary @P2 @TC-PI-012
  Scenario: Tracking a view twice on the same post is idempotent
    Given I am logged in with valid credentials
    And a post exists that was created by another user
    When I track a view on the post twice
    Then both responses should have status 200

  @boundary @P2 @TC-PI-013
  Scenario: Reporting the same post twice returns 400 or 409
    Given I am logged in with valid credentials
    And I have already reported a post
    When I report the same post again
    Then the response status should be 400 or 409

  @security @P1 @TC-PI-014
  Scenario: Report post without x-api-key returns 401 or 403
    Given the API key header is not set
    When I report a post
    Then the response status should be 401 or 403
