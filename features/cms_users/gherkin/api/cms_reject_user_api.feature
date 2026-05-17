@api @cms @reject
Feature: CMS Reject User API
  As a CMS admin
  I want to reject user applications
  So that unqualified users cannot access the Hono platform

  Background:
    Given the API is available
    And I am authenticated as CMS admin

  @smoke @P0 @TC-CMS-REJECT-001
  Scenario: Reject verified user returns 200 and status REJECTED
    Given a verified user exists in DB
    When CMS admin rejects user with valid reason
    Then response status should be 200
    And user status in DB should be REJECTED

  @boundary @P1 @TC-CMS-REJECT-002
  Scenario: Reject without reason body
    Given a verified user exists
    When CMS admin rejects without reason field
    Then response should be 200 or 400

  @boundary @P1 @TC-CMS-REJECT-003
  Scenario: Reject with empty reason string
    When CMS admin rejects with reason ""
    Then response should be 200 or 400

  @security @P0 @TC-CMS-REJECT-004
  Scenario: Reject without token returns 401
    Given I am not authenticated
    When CMS admin rejects the user
    Then response status should be 401

  @negative @P0 @TC-CMS-REJECT-005
  Scenario: Reject with invalid user ID returns 404
    When CMS admin rejects non-existent user ID
    Then response status should be 404

  @boundary @P2 @TC-CMS-REJECT-006 @dev-bug
  Scenario: Reject already approved user — business rule unclear
    Given an APPROVED user exists
    When CMS admin tries to reject them
    Then behavior should be documented (400 or 200)

  @boundary @P2 @TC-CMS-REJECT-007 @dev-bug
  Scenario: Reject already rejected user — should be idempotent
    Given a user was already rejected
    When CMS admin rejects again
    Then response should be 200 or 400

  @edge @P2 @TC-CMS-REJECT-008 @dev-bug
  Scenario: Reject PENDING unverified user
    Given a user registered but not verified email
    When CMS admin rejects them
    Then behavior should be documented

  @boundary @P2 @TC-CMS-REJECT-009
  Scenario: Reject with very long reason (1000+ chars)
    When CMS admin rejects with reason of 1200 characters
    Then response should be 200 or 400

  @combination @P1 @TC-CMS-REJECT-010 @dev-bug
  Scenario: Reject then approve same user
    Given a user is rejected
    When CMS admin approves the same user
    Then behavior and final status should be documented
