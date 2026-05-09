@web @login
Feature: Login Web — app-dev.thehono.com
  As a registered user
  I want to login via web browser
  So that I can access the Hono platform

  Background:
    Given I am on the login page

  @boundary @P1 @TC-WEB-001
  Scenario: Login button disabled when fields empty
    When I have not entered any credentials
    Then the login button should be disabled

  @boundary @P1 @TC-WEB-002
  Scenario: Login button disabled with email only
    When I enter the valid email
    And I leave the password field empty
    Then the login button should be disabled

  @smoke @P0 @TC-WEB-003
  Scenario: Login button enabled when both fields filled
    When I enter the valid email
    And I enter the valid password
    Then the login button should be enabled

  @security @P1 @TC-WEB-004
  Scenario Outline: Invalid email formats blocked by frontend
    When I enter "<email>" as email
    And I enter any password
    Then the login button should be disabled

    Examples: Invalid email cases
      | email                          | reason         |
      | bad-email                      | invalid format |
      | '; DROP TABLE users;--         | SQL injection  |
      | test@                          | incomplete     |

  @self-healing @P2 @TC-WEB-005
  Scenario: Self-healing locator auto-recovery
    When a locator is broken
    Then the self-healer should find a working alternative
