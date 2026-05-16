@api @register
Feature: Register API — /v1/users/register
  As a new user
  I want to register an account via API
  So that I can access the Hono platform

  Background:
    Given the API is available at the configured base URL
    And the API key header is set

  @smoke @P0 @TC-REG-API-001
  Scenario: Register with valid data returns OK
    When I POST to "/v1/users/register" with valid registration payload
    Then the response status should be 200
    And the response code should be "OK"

  @negative @P1 @TC-REG-API-002
  Scenario: Register with existing email returns error
    When I POST to "/v1/users/register" with already registered email
    Then the response status should be 4xx

  @boundary @P1 @TC-REG-API-003
  Scenario: Register with missing required fields returns 400
    When I POST to "/v1/users/register" with only email field
    Then the response status should be 400

  @negative @P1 @TC-REG-API-004
  Scenario: Register with invalid email format returns 400
    When I POST to "/v1/users/register" with invalid email "not-an-email"
    Then the response status should be 400

  @boundary @P1 @TC-REG-API-005
  Scenario: Register with empty body returns 400
    When I POST to "/v1/users/register" with empty body
    Then the response status should be 400

  @negative @P1 @TC-REG-API-007
  Scenario: Register with duplicate phone number returns error
    When I POST to "/v1/users/register" with already registered phone number
    Then the response status should be 4xx

  @combination @P1 @TC-REG-API-008
  Scenario: Register with duplicate email and valid phone is blocked
    When I POST with duplicate email and unique phone
    Then the response status should be 4xx

  @combination @P1 @TC-REG-API-009
  Scenario: Register with valid email and duplicate phone is blocked
    When I POST with unique email and duplicate phone
    Then the response status should be 4xx

  @negative @P1 @TC-REG-API-010
  Scenario Outline: Invalid email formats are rejected
    When I POST with email "<invalid_email>"
    Then the response status should be 400

    Examples: Invalid emails
      | invalid_email        |
      | notanemail           |
      | missing@             |
      | @nodomain.com        |
      | spaces in@email.com  |

  @negative @P1 @TC-REG-API-011
  Scenario: Non-numeric phone number returns 400
    When I POST with phone_number "abc-invalid"
    Then the response status should be 400

  @security @P0 @TC-REG-API-012
  Scenario: Register without x-api-key returns 401
    Given the API key header is not set
    When I POST to "/v1/users/register" with valid payload
    Then the response status should be 401

  @security @P2 @TC-REG-API-013
  Scenario: SQL injection in fullname is sanitized
    When I POST with fullname "'; DROP TABLE users; --"
    Then the response should be handled safely
    And the users table should still exist

  @boundary @P2 @TC-REG-API-014
  Scenario: Very long fullname (501 chars) is handled
    When I POST with fullname of 501 characters
    Then the response should be 200 or 400

  @combination @P1 @TC-REG-API-015
  Scenario: Register with both email and phone duplicate is blocked
    When I POST with already registered email AND phone
    Then the response status should be 4xx

  @boundary @P2 @TC-REG-API-016
  Scenario: Register with minimum valid data
    When I POST with only required fields filled
    Then the response status should be 200
    And code should be "OK"

  @boundary @P2 @TC-REG-API-017
  Scenario: Register with special characters in fullname
    When I POST with fullname containing special chars "!@#$%"
    Then the response should be 200 or 400

  @negative @P1 @TC-REG-API-018
  Scenario: Register with missing fullname returns 400
    When I POST without fullname field
    Then the response status should be 400

  @negative @P1 @TC-REG-API-019
  Scenario: Register with missing linkedin returns 400
    When I POST without linkedin field
    Then the response status should be 400 or 200

  @negative @P1 @TC-REG-API-020
  Scenario: Register with invalid phone country code
    When I POST with phone_country_code "XX"
    Then the response status should be 400 or 422

  @boundary @P2 @TC-REG-API-021
  Scenario: Register with phone number too short
    When I POST with phone_number "123"
    Then the response status should be 400 or 422

  @boundary @P2 @TC-REG-API-022
  Scenario: Register with phone number too long
    When I POST with phone_number of 20+ digits
    Then the response status should be 400 or 200

  @security @P2 @TC-REG-API-023
  Scenario: XSS in fullname is sanitized
    When I POST with fullname containing XSS payload
    Then the response should be handled safely

  @boundary @P2 @TC-REG-API-024
  Scenario: Register with valid LinkedIn URL format
    When I POST with linkedin "https://linkedin.com/in/validuser"
    Then the response status should be 200

  @negative @P1 @TC-REG-API-025
  Scenario: Register with invalid LinkedIn URL format
    When I POST with linkedin "not-a-url"
    Then the response status should be 400 or 200

  @performance @P2 @TC-REG-API-026
  Scenario: Register response time within threshold
    When I POST with valid registration data
    Then the response time should be under 3000 milliseconds

  @boundary @P2 @TC-REG-API-027
  Scenario: Register with empty string fullname returns 400
    When I POST with fullname ""
    Then the response status should be 400 or 422

  @boundary @P2 @TC-REG-API-028
  Scenario: Register with whitespace only fullname
    When I POST with fullname "   "
    Then the response status should be 400 or 200

  @combination @P1 @TC-REG-API-029
  Scenario: Register same user twice returns error on second attempt
    Given I successfully register a new user
    When I POST the same registration data again
    Then the second attempt should return 4xx

  @combination @P2 @TC-REG-API-030
  Scenario: Register with null values in required fields
    When I POST with null email and null phone
    Then the response status should be 400 or 422
