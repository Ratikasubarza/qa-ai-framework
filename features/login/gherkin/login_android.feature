@mobile @android @login
Feature: Login Android — app.thehono.development
  As a mobile user
  I want to login via the Android app
  So that I can access Hono on my device

  Background:
    Given the Hono Android app is launched
    And I navigate to the login screen

  @smoke @P0 @TC-MOB-001
  Scenario: Valid credentials navigate to feed
    When I enter the valid email in the email field
    And I enter the valid password in the password field
    And I tap the login button
    Then I should see the feed screen

  @negative @P1 @TC-MOB-002
  Scenario: Wrong password shows error
    When I enter the valid email in the email field
    And I enter "WrongPass!" in the password field
    And I tap the login button
    Then I should see an error message

  @boundary @P1 @TC-MOB-003
  Scenario: Login button disabled when fields empty
    When I have not entered any credentials
    Then the login button should be disabled

  @boundary @P1 @TC-MOB-004
  Scenario: Login button disabled with email only
    When I enter the valid email in the email field
    And I leave the password field empty
    Then the login button should be disabled

  @boundary @P1 @TC-MOB-005
  Scenario: Login button disabled with password only
    When I leave the email field empty
    And I enter the valid password in the password field
    Then the login button should be disabled
