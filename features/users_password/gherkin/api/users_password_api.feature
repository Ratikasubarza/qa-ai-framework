Feature: User password API
  As an authenticated user
  I want to change my password
  So that my account credential can be rotated securely

  Background:
    Given an approved synthetic user exists
    And the user is authenticated with the current password

  @api @smoke @security
  Scenario: Change password with valid current password
    When I change my password with the current password and a new password
    Then the API returns 200
    And the old password can no longer be used to login
    And the new password can be used to login

  @api @security @negative
  Scenario: Change password without bearer token
    When I change my password without an Authorization header
    Then the API returns 401

  @api @negative
  Scenario: Change password with wrong current password
    When I change my password with a wrong current password
    Then the API rejects the request
    And the original password still works

  @api @negative @boundary
  Scenario Outline: Change password with missing required field
    When I change my password without "<field>"
    Then the API returns a validation error

    Examples:
      | field            |
      | current_password |
      | new_password     |
