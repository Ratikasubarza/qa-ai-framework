@api @admin_moderation
Feature: Admin Moderation API
  As an admin user
  I want to list, hide, dismiss, and unhide reported posts
  So that I can moderate content on the Hono platform

  Background:
    Given the API is available at the configured base URL
    And the API key header is set

  # ── List Reported Posts ──────────────────────────────────────────────────────

  @smoke @P0 @TC-AM-001
  Scenario: Admin lists reported posts with PENDING status
    Given I am logged in as an admin
    When I request the reported posts list with status "PENDING"
    Then the response status should be 200
    And the response code should be "OK"
    And each item should contain fields "status", "post" with "id"

  @smoke @P0 @TC-AM-002
  Scenario: Admin lists reported posts with HIDDEN status
    Given I am logged in as an admin
    And at least one post has been hidden
    When I request the reported posts list with status "HIDDEN"
    Then the response status should be 200
    And all returned posts should have "is_hidden" equal to true

  @smoke @P0 @TC-AM-003
  Scenario: Admin lists reported posts with DISMISSED status
    Given I am logged in as an admin
    When I request the reported posts list with status "DISMISSED"
    Then the response status should be 200
    And the response code should be "OK"

  @boundary @P2 @TC-AM-004
  Scenario: List reported posts with per_page=100 (maximum)
    Given I am logged in as an admin
    When I request the reported posts list with per_page 100
    Then the response status should be 200
    And the response should contain at most 100 items

  @negative @P1 @TC-AM-005
  Scenario: List reported posts with per_page=101 is rejected
    Given I am logged in as an admin
    When I request the reported posts list with per_page 101
    Then the response status should be 422

  @negative @P1 @TC-AM-006
  Scenario: List reported posts with invalid status filter is rejected
    Given I am logged in as an admin
    When I request the reported posts list with status "INVALID_STATUS"
    Then the response status should be 422

  @security @P0 @TC-AM-007
  Scenario: List reported posts without x-api-key returns 401
    Given the API key header is not set
    When I request the reported posts list
    Then the response status should be 401

  @security @P0 @TC-AM-008
  Scenario: List reported posts with non-admin token returns 403
    Given I am logged in as a regular user
    When I request the reported posts list
    Then the response status should be 403

  # ── Hide Post ────────────────────────────────────────────────────────────────

  @smoke @P0 @TC-AM-009
  Scenario: Admin hides a reported post successfully
    Given I am logged in as an admin
    And a post has been reported and is in PENDING state
    When I hide the reported post
    Then the response status should be 200
    And the response code should be "OK"

  @negative @P1 @TC-AM-010
  Scenario: Admin cannot hide a post that is already hidden
    Given I am logged in as an admin
    And a post is already in HIDDEN state
    When I hide the post again
    Then the response status should be 422
    And the response code should be "NOKUNPROC"
    And the error message should contain "already hidden"

  @negative @P1 @TC-AM-011
  Scenario: Hide non-existent post returns 404
    Given I am logged in as an admin
    When I hide post "00000000-0000-0000-0000-000000000000"
    Then the response status should be 404

  @security @P0 @TC-AM-012
  Scenario: Hide post without x-api-key returns 401
    Given the API key header is not set
    When I hide a reported post
    Then the response status should be 401

  # ── Dismiss Post Reports ─────────────────────────────────────────────────────

  @smoke @P0 @TC-AM-013
  Scenario: Admin dismisses reports on a pending post successfully
    Given I am logged in as an admin
    And a post has been reported and is in PENDING state
    When I dismiss the reports for the post
    Then the response status should be 200
    And the response code should be "OK"

  @negative @P1 @TC-AM-014
  Scenario: Admin cannot dismiss reports on a hidden post
    Given I am logged in as an admin
    And a post is already in HIDDEN state
    When I dismiss the reports for the hidden post
    Then the response status should be 422
    And the response code should be "NOKUNPROC"
    And the error message should contain "hidden"

  @negative @P1 @TC-AM-015
  Scenario: Dismiss reports on a post with no pending reports is rejected
    Given I am logged in as an admin
    And a post exists with no pending reports
    When I dismiss the reports for that post
    Then the response status should be 404 or 422

  @negative @P1 @TC-AM-016
  Scenario: Dismiss reports on non-existent post returns 404
    Given I am logged in as an admin
    When I dismiss reports for post "00000000-0000-0000-0000-000000000000"
    Then the response status should be 404

  @security @P0 @TC-AM-017
  Scenario: Dismiss reports without x-api-key returns 401
    Given the API key header is not set
    When I dismiss reports for a post
    Then the response status should be 401

  # ── Unhide Post ──────────────────────────────────────────────────────────────

  @smoke @P0 @TC-AM-018
  Scenario: Admin unhides a hidden post successfully
    Given I am logged in as an admin
    And a post is in HIDDEN state
    When I unhide the post
    Then the response status should be 200
    And the response code should be "OK"

  @negative @P1 @TC-AM-019
  Scenario: Admin cannot unhide a post that is not hidden
    Given I am logged in as an admin
    And a post is in PENDING state (not hidden)
    When I unhide the post
    Then the response status should be 422
    And the response code should be "NOKUNPROC"
    And the error message should contain "not hidden"

  @negative @P1 @TC-AM-020
  Scenario: Unhide non-existent post returns 404
    Given I am logged in as an admin
    When I unhide post "00000000-0000-0000-0000-000000000000"
    Then the response status should be 404

  @security @P0 @TC-AM-021
  Scenario: Unhide post without x-api-key returns 401
    Given the API key header is not set
    When I unhide a hidden post
    Then the response status should be 401
