@api @posts
Feature: Create Post API
  As an authenticated user
  I want to create a post via API
  So that I can share content on the Hono platform

  Background:
    Given the API is available at the configured base URL
    And the API key header is set

  @smoke @P0 @TC-POST-API-001
  Scenario: Valid post creation returns OK
    Given I am logged in with valid credentials
    When I create a post with valid content and at least 1 topic
    Then the response status should be 200
    And the response code should be "OK"
    And the response body should contain a post id

  @smoke @P0 @TC-POST-API-002
  Scenario: Create post with media attachment returns OK
    Given I am logged in with valid credentials
    When I create a post with valid content and a media URL
    Then the response status should be 200
    And the response code should be "OK"
    And the response body should contain a post id

  @boundary @P1 @TC-POST-API-003
  Scenario: Create anonymous post sets is_anonymous true in response
    Given I am logged in with valid credentials
    When I create a post with is_anonymous set to true
    Then the response status should be 200
    And the response body field "is_anonymous" should be true

  @boundary @P1 @TC-POST-API-004
  Scenario: Create post with multiple topics returns all topics in response
    Given I am logged in with valid credentials
    When I create a post with 3 topic_ids
    Then the response status should be 200
    And the response body "topics" array should not be empty

  @smoke @P0 @TC-POST-API-005
  Scenario: New post response contains all required fields
    Given I am logged in with valid credentials
    When I create a post with valid post payload
    Then the response status should be 200
    And the response body should contain fields "id", "content", "visibility", "is_anonymous", "topics", "engagement", "created_at"
    And all engagement counts should be 0

  @boundary @P2 @TC-POST-API-006
  Scenario: Create post with visibility EVERYONE is accepted
    Given I am logged in with valid credentials
    When I create a post with visibility "EVERYONE"
    Then the response status should be 200

  @security @P0 @TC-POST-API-007
  Scenario: Create post without auth token returns 401
    Given I am not authenticated
    When I create a post with valid post payload
    Then the response status should be 401

  @security @P0 @TC-POST-API-008
  Scenario: Create post without x-api-key returns 401
    Given the API key header is not set
    When I create a post with valid post payload
    Then the response status should be 401

  @negative @P1 @TC-POST-API-009
  Scenario: Create post with empty topic_ids returns 422
    Given I am logged in with valid credentials
    When I create a post with topic_ids as empty array
    Then the response status should be 422
    And the response code should be "NOKUNPROC"
    And the error message should contain "topic"

  @negative @P1 @TC-POST-API-010
  Scenario Outline: Missing or empty required fields are rejected
    Given I am logged in with valid credentials
    When I create a post with <condition>
    Then the response status should be 400 or 422

    Examples: Required field validation
      | condition                      |
      | content as empty string        |
      | content field missing          |
      | topic_ids field missing        |
      | completely empty body          |

  @negative @P1 @TC-POST-API-012
  Scenario: Create post with invalid visibility value is rejected
    Given I am logged in with valid credentials
    When I create a post with visibility "INVALID_VISIBILITY"
    Then the response status should be 400 or 422

  @combination @P2 @TC-POST-API-017
  Scenario: Create post mentioning user who disabled mentions returns 422
    Given I am logged in with valid credentials
    When I create a post mentioning a user who has disabled tagging
    Then the response status should be 422
    And the response code should be "NOKUNPROC"
    And the error message should contain "mention"

  @boundary @P2 @TC-POST-API-014
  Scenario: Create post with very long content (5000 characters)
    Given I am logged in with valid credentials
    When I create a post with content of 5000 characters
    Then the response should be 200 or 400

  @performance @P2 @TC-POST-API-016
  Scenario: Create post response time within threshold
    Given I am logged in with valid credentials
    When I create a post with valid post payload
    Then the response status should be 200
    And the response time should be under 3000 milliseconds
