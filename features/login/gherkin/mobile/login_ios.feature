@mobile @ios @login @pending
Feature: Login iOS — app.thehono (Pending Implementation)
  Note: iOS testing requires macOS + Xcode + physical device or simulator.
  Will be implemented after Android test suite is fully stable.
  All scenarios mirror the Android login test suite.

  @smoke @P0 @TC-MOB-IOS-001 @pending
  Scenario: Login with valid credentials reaches feed screen
    Given the Hono iOS app is launched
    When I enter valid email and password
    And I tap the login button
    Then I should see the feed screen

  @negative @P1 @TC-MOB-IOS-002 @pending
  Scenario: Login with wrong password shows error
    When I enter valid email and wrong password
    And I tap the login button
    Then I should see an error message

  @boundary @P1 @TC-MOB-IOS-003 @pending
  Scenario: Login button disabled when fields empty
    Given no credentials have been entered
    Then the login button should be disabled

  @boundary @P1 @TC-MOB-IOS-004 @pending
  Scenario: Login button disabled with email only
    When I enter only email without password
    Then the login button should be disabled

  @boundary @P1 @TC-MOB-IOS-005 @pending
  Scenario: Login button disabled with password only
    When I enter only password without email
    Then the login button should be disabled
