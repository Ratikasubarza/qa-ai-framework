Feature: User account API
  As an authenticated user
  I want to retrieve and update my account information
  So that account identity and phone metadata can be shown safely

  Background:
    Given an approved synthetic user exists
    And the user is authenticated

  @api @smoke
  Scenario: Get account information with a valid bearer token
    When I GET "/v1/users/me/account"
    Then the API returns 200
    And the response contains the authenticated user's email
    And the response contains account phone metadata

  @api @security @negative
  Scenario: Get account information without bearer token
    When I GET "/v1/users/me/account" without an Authorization header
    Then the API returns 401

  @api @regression
  Scenario: Legacy account information supports nullable country metadata
    When I GET "/v1/users/me/account"
    Then phone_country_iso may be null for legacy users
    And nationality may be null for legacy users

  @api @smoke
  Scenario: Update account information with valid country metadata
    When I PUT "/v1/users/me/account" with phone number, phone code, and nationality id
    Then the API returns 200
    And the response confirms account data is saved
    And the updated account phone metadata can be retrieved

  @api @security @negative
  Scenario: Update account information without bearer token
    When I PUT "/v1/users/me/account" without an Authorization header
    Then the API returns 401

  @api @negative
  Scenario: Update account information with invalid phone code
    When I PUT "/v1/users/me/account" with an invalid phone code
    Then the API returns a validation error
    And the response explains that the phone code is unknown
