Feature: User email API
  As an authenticated user
  I want to request an email change
  So that my account email can be updated securely

  Background:
    Given an approved synthetic user exists
    And the user is authenticated

  @api @smoke
  Scenario: Request email change with a new email address
    When I request an email change with a unique new email
    Then the API returns 200
    And the response confirms the email change request is saved

  @api @security @negative
  Scenario: Request email change without bearer token
    When I request an email change without an Authorization header
    Then the API returns 401

  @api @negative
  Scenario: Request email change to an email already in use
    Given another approved synthetic user exists
    When I request an email change using the other user's email
    Then the API returns a validation error
    And the response says the email already exists

  @api @smoke
  Scenario: Verify email change with a valid code
    Given an authenticated user requested an email change
    When I verify my email change with the latest verification code
    Then the API returns 200
    And the response says the email was updated successfully

  @api @negative
  Scenario: Verify email change with an expired code
    Given an authenticated user requested an email change
    And the latest verification code is expired
    When I verify my email change with the expired verification code
    Then the API returns 410
    And the response says the verification link has expired
