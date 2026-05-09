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
