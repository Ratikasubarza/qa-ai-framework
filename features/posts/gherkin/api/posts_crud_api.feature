@api @posts
Feature: Posts CRUD API
  As an authenticated user
  I want to read, edit, change visibility, delete my posts
  And browse user posts, media, and mentionable users
  So that I can fully manage post content on the platform

  Background:
    Given the API is available at the configured base URL
    And the API key header is set
    And I am logged in as a registered user
    And a post has been created for this test module

  # ── GET /v1/posts/:post_id ────────────────────────────────────────────────────

  @smoke @P0 @TC-POST-API-020
  Scenario: Get post detail by valid post_id returns 200
    When I GET /v1/posts/:post_id with a valid Bearer token
    Then the response status should be 200
    And the response data should contain "id" equal to the requested post_id

  @negative @P1 @TC-POST-API-021
  Scenario: Get post with non-existent post_id returns 404
    When I GET /v1/posts/00000000-0000-0000-0000-000000000000 with a valid Bearer token
    Then the response status should be 400 or 404

  @security @P0 @TC-POST-API-022
  Scenario: Get post without auth token returns 401
    Given I am not authenticated
    When I GET /v1/posts/:post_id without a Bearer token
    Then the response status should be 401

  # ── PUT /v1/posts/:post_id ────────────────────────────────────────────────────

  @smoke @P0 @TC-POST-API-023
  Scenario: Edit post content returns 200
    When I PUT /v1/posts/:post_id with content "Updated QA test post content" and valid topic_ids
    Then the response status should be 200 or 201

  @security @P0 @TC-POST-API-024
  Scenario: Edit post without auth token returns 401
    Given I am not authenticated
    When I PUT /v1/posts/:post_id with content "Unauthorized edit" and no Bearer token
    Then the response status should be 401

  @negative @P1 @TC-POST-API-025
  Scenario: Edit non-existent post returns 403 or 404
    When I PUT /v1/posts/00000000-0000-0000-0000-000000000000 with content "Ghost edit"
    Then the response status should be 403 or 404

  # ── PUT /v1/posts/:post_id/visibility ─────────────────────────────────────────

  @smoke @P0 @TC-POST-API-026
  Scenario: Change post visibility to EVERYONE returns 200
    When I PUT /v1/posts/:post_id/visibility with visibility "EVERYONE"
    Then the response status should be 200 or 201

  @negative @P1 @TC-POST-API-027
  Scenario: Change post visibility with invalid value returns 400 or 422
    When I PUT /v1/posts/:post_id/visibility with visibility "PRIVATE_MODE"
    Then the response status should be 400 or 422

  @security @P0 @TC-POST-API-028
  Scenario: Change post visibility without auth returns 401
    Given I am not authenticated
    When I PUT /v1/posts/:post_id/visibility with visibility "PUBLIC" and no Bearer token
    Then the response status should be 401

  # ── GET /v1/users/:user_id/posts ─────────────────────────────────────────────

  @smoke @P0 @TC-POST-API-029
  Scenario: Get own user posts returns 200
    When I GET /v1/users/:user_id/posts with params page=1, per_page=10
    Then the response status should be 200

  @security @P0 @TC-POST-API-030
  Scenario: Get user posts without auth returns 401
    Given I am not authenticated
    When I GET /v1/users/:user_id/posts without a Bearer token
    Then the response status should be 401

  # ── GET /v1/users/:id/media ───────────────────────────────────────────────────

  @smoke @P0 @TC-POST-API-031
  Scenario: Get user media returns 200
    When I GET /v1/users/:user_id/media with params page=1, per_page=10
    Then the response status should be 200

  @security @P0 @TC-POST-API-032
  Scenario: Get user media without auth returns 401
    Given I am not authenticated
    When I GET /v1/users/:user_id/media without a Bearer token
    Then the response status should be 401

  # ── GET /v1/users/mentionable ─────────────────────────────────────────────────

  @smoke @P0 @TC-POST-API-033
  Scenario: Get mentionable users typeahead returns 200
    When I GET /v1/users/mentionable with param query="test"
    Then the response status should be 200

  @security @P0 @TC-POST-API-034
  Scenario: Get mentionable users without auth returns 401
    Given I am not authenticated
    When I GET /v1/users/mentionable with param query="test" and no Bearer token
    Then the response status should be 401

  # ── DELETE /v1/posts/:post_id ─────────────────────────────────────────────────

  @security @P0 @TC-POST-API-035
  Scenario: Delete post without auth returns 401
    Given I am not authenticated
    When I DELETE /v1/posts/:post_id without a Bearer token
    Then the response status should be 401

  @negative @P1 @TC-POST-API-036
  Scenario: Delete non-existent post returns 403 or 404
    When I DELETE /v1/posts/00000000-0000-0000-0000-000000000000 with a valid Bearer token
    Then the response status should be 403 or 404

  @smoke @P0 @TC-POST-API-037
  Scenario: Delete own post returns 200 or 204
    Given I create a new post inline for deletion
    When I DELETE /v1/posts/:new_post_id with a valid Bearer token
    Then the response status should be 200 or 204
