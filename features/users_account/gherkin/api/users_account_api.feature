Feature: User account API
  As an authenticated user
  I want to retrieve my account information
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
