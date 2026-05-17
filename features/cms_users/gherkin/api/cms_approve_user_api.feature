@api @cms @approve
Feature: CMS Approve User API
  As a CMS admin
  I want to approve registered users
  So that they can access the Hono platform

  Background:
    Given the API is available at the configured base URL
    And I am authenticated as CMS admin

  @smoke @P0 @TC-CMS-APPROVE-001
  Scenario: Full flow — Register then approve user
    Given a new user registers via API
    And the user has PENDING status in the database
    When CMS admin approves the user by ID from database
    Then the response status should be 200
    And the user status in database should be APPROVED

  @negative @P1 @TC-CMS-APPROVE-002
  Scenario: Approve with invalid user ID returns 404
    When CMS admin approves user with non-existent ID
    Then the response status should be 404

  @security @P0 @TC-CMS-APPROVE-003
  Scenario: Approve without token returns 401
    Given I am not authenticated
    When CMS admin approves the user
    Then the response status should be 401

  @boundary @P2 @TC-CMS-APPROVE-004
  Scenario: Approve already approved user is handled gracefully
    Given a user with APPROVED status exists in database
    When CMS admin approves the same user again
    Then the response status should be 200 or 400
