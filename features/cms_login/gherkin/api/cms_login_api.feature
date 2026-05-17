@api @cms @login
Feature: CMS Login API — api-dev.thehono.com
  As a CMS admin user
  I want to login via API with admin resource
  So that I can access the Hono CMS Dashboard

  Background:
    Given the API is available at the configured base URL
    And the API key header is set

  @smoke @P0 @TC-CMS-API-001
  Scenario: Valid CMS credentials return access token
    When I log in to CMS with email, password and resource "admin"
    Then the response status should be 200
    And the response body should contain an access token

  @negative @P1 @TC-CMS-API-002
  Scenario: Wrong password returns 401
    When I log in to CMS with wrong password and resource "admin"
    Then the response status should be 401

  @boundary @P1 @TC-CMS-API-003
  Scenario: Missing resource field returns error
    When I log in to CMS without resource field
    Then the response status should be 4xx

  @negative @P1 @TC-CMS-API-004
  Scenario: Wrong resource value returns error
    When I log in to CMS with resource "invalid_resource"
    Then the response status should be 4xx

  @performance @P2 @TC-CMS-API-005
  Scenario: CMS login response time within threshold
    When I log in to CMS with valid CMS credentials
    Then the response time should be under 3000 milliseconds

  @security @P0 @TC-CMS-API-006
  Scenario: Login without x-api-key header returns 401
    Given the API key header is not set
    When I log in to CMS with valid CMS credentials
    Then the response status should be 401

  @negative @P1 @TC-CMS-API-007
  Scenario: Login with invalid email format returns error
    When I log in to CMS with email "not-an-email" and resource "admin"
    Then the response status should be 400 or 422

  @negative @P1 @TC-CMS-API-008
  Scenario: Login with empty email returns error
    When I log in to CMS with empty email
    Then the response status should be 400 or 422

  @negative @P1 @TC-CMS-API-009
  Scenario: Login with empty password returns error
    When I log in to CMS with empty password
    Then the response status should be 400 or 422

  @boundary @P2 @TC-CMS-API-010
  Scenario: Multiple failed login attempts
    When I log in to CMS with wrong password 3 times
    Then each response status should be 401
