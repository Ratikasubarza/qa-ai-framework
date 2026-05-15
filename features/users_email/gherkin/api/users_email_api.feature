Feature: User email API
  As an authenticated user
  I want to request an email change
  So that my account email can be updated securely

  Background:
    Given an approved synthetic user exists
    And the user is authenticated

  @api @smoke
  Scenario: Request email change with a new email address
    When I PUT "/v1/users/me/email" with a unique new email
    Then the API returns 200
    And the response confirms the email change request is saved

  @api @security @negative
  Scenario: Request email change without bearer token
    When I PUT "/v1/users/me/email" without an Authorization header
    Then the API returns 401

  @api @negative
  Scenario: Request email change to an email already in use
    Given another approved synthetic user exists
    When I PUT "/v1/users/me/email" using the other user's email
    Then the API returns a validation error
    And the response says the email already exists
