@api @login
Feature: Login API — api-dev.thehono.com
  As a client application
  I want to authenticate via API
  So that I can receive a valid access token

  Background:
    Given the API is available at the configured base URL
    And the API key header is set

  @smoke @P0 @TC-API-001
  Scenario: Valid credentials return access token
    When I login with the valid email and password
    Then the response status should be 200
    And the response body should contain an access token

  @negative @P1 @TC-API-002
  Scenario Outline: Invalid login attempts return error
    When I login with email "<email>" and password "<password>"
    Then the response status should be <status>

    Examples: Invalid login cases
      | email                        | password      | status | reason         |
      | testingHonoA@mailinator.com  | WrongPass123! | 401    | wrong password |
      | bad-email                    | AnyPass123!   | 400    | invalid email  |

  @boundary @P1 @TC-API-004
  Scenario Outline: Missing required fields return 400
    When I POST to login with <missing_field> missing
    Then the response status should be 400

    Examples: Missing fields
      | missing_field |
      | password      |
      | email         |
      | both fields   |

  @smoke @P0 @TC-API-006
  Scenario: Authenticated search returns results
    Given I am logged in with valid credentials
    When I search for "test"
    Then the response status should be 200

  @security @P1 @TC-API-007
  Scenario: Unauthenticated search returns 401
    Given I am not authenticated
    When I search for "test"
    Then the response status should be 401

  @performance @P2 @TC-API-009
  Scenario: Login response time within threshold
    When I login with valid credentials
    Then the response time should be under 3000 milliseconds

  @smoke @P0 @TC-API-010
  Scenario: Authenticated user can get their profile
    Given I am logged in with valid credentials
    When I GET "/v1/users/me"
    Then the response status should be 200
    And the response body should contain profile data

  @security @P1 @TC-API-011
  Scenario: Unauthenticated user cannot get profile
    Given I am not authenticated
    When I GET "/v1/users/me"
    Then the response status should be 401

  # ── Register Scenarios ────────────────────────────────────────────────

  @smoke @P0 @TC-API-012
  Scenario: Register with valid data returns OK
    When I POST to "/v1/users/register" with valid registration data
    Then the response status should be 200
    And the response body code should be "OK"

  @negative @P1 @TC-API-013
  Scenario: Register with duplicate email returns error
    When I POST to "/v1/users/register" with already registered email
    Then the response status should be 4xx

  @boundary @P1 @TC-API-014
  Scenario: Register with missing required fields returns 400
    When I POST to "/v1/users/register" with only email field
    Then the response status should be 400

  @negative @P1 @TC-API-015
  Scenario: Register with invalid email format returns 400
    When I POST to "/v1/users/register" with invalid email "not-an-email"
    Then the response status should be 400

  @smoke @P0 @TC-API-010
  Scenario: Authenticated user can get their profile
    Given I am logged in with valid credentials
    When I GET "/v1/users/me"
    Then the response status should be 200
    And the response body should contain profile data

  @security @P1 @TC-API-011
  Scenario: Unauthenticated user cannot get profile
    Given I am not authenticated
    When I GET "/v1/users/me"
    Then the response status should be 401

  @security @P1 @TC-API-012
  Scenario: Login without x-api-key header returns 401
    Given the API key header is not set
    When I POST to "/v1/users/login" with valid credentials
    Then the response status should be 401

  @negative @P1 @TC-API-013
  Scenario: Login with empty email returns 400
    When I POST to "/v1/users/login" with empty email
    Then the response status should be 400

  @negative @P1 @TC-API-014
  Scenario: Login with empty password returns 400
    When I POST to "/v1/users/login" with empty password
    Then the response status should be 400

  @negative @P1 @TC-API-015
  Scenario: Login with invalid email format returns 400
    When I POST to "/v1/users/login" with email "notanemail"
    Then the response status should be 400

  @performance @P2 @TC-API-016
  Scenario: Login response time within threshold
    When I POST to "/v1/users/login" with valid credentials
    Then the response time should be under 3000 milliseconds

  @security @P2 @TC-API-017
  Scenario: SQL injection in email is blocked
    When I POST to "/v1/users/login" with email "' OR 1=1 --"
    Then the response status should be 400 or 401

  @security @P2 @TC-API-018
  Scenario: Very long email is handled gracefully
    When I POST to "/v1/users/login" with email of 500 characters
    Then the response status should be 400 or 401

  @boundary @P2 @TC-API-019
  Scenario: Login with correct email wrong case
    When I POST to "/v1/users/login" with email in uppercase
    Then the response should indicate case sensitivity behavior

  @security @P2 @TC-API-020
  Scenario: Multiple failed logins
    When I POST to "/v1/users/login" with wrong password 3 times
    Then each response should be 401

  @negative @P1 @TC-API-021
  Scenario: Login with empty body returns 400
    When I POST to "/v1/users/login" with empty body
    Then the response status should be 400

  @negative @P1 @TC-API-022
  Scenario: Login with missing password field returns 400
    When I POST to "/v1/users/login" with only email field
    Then the response status should be 400
