@mobile @android @register
Feature: Register Android — app.thehono.development
  As a new user
  I want to register via the Android app
  So that I can apply to join the Hono community

  Background:
    Given the Hono Android app is launched
    And I tap "Join our community"
    And I am on the register screen

  @smoke @P0 @TC-MOB-REG-001
  Scenario: Register with valid data shows verify email screen
    When I fill the full name field
    And I fill the email field with unique email
    And I fill the phone number field
    And I fill the LinkedIn profile field
    And I tap "Apply now"
    Then I should see "Please verify your email" screen

  @boundary @P1 @TC-MOB-REG-002
  Scenario: Apply button disabled when form is empty
    When I have not filled any fields
    Then the "Apply now" button should be disabled

  @boundary @P1 @TC-MOB-REG-003
  Scenario: Apply button disabled with partial form
    When I fill only name and email fields
    Then the "Apply now" button should be disabled

  @negative @P1 @TC-MOB-REG-004
  Scenario: Invalid email format is blocked
    When I fill the form with invalid email "not-an-email"
    Then I should not see the verify email screen

  @negative @P1 @TC-MOB-REG-005
  Scenario: Duplicate email shows error
    When I fill the form with already registered email
    And I tap "Apply now"
    Then I should see an error or not proceed to verify screen
