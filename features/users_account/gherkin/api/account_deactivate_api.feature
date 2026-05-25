@api @users_account
Feature: Account Deactivate API
  As an authenticated user
  I want to deactivate my account using my password
  So that I can permanently disable access to my profile

  Background:
    Given the API is available at the configured base URL
    And the API key header is set
    And a dedicated deactivate_user account has been created for this module

  # ── POST /v1/users/me/deactivate ─────────────────────────────────────────────

  @smoke @P0 @TC-ACC-010
  Scenario: Deactivate account with correct password returns 200
    Given I am logged in as the deactivate_user
    When I POST to /v1/users/me/deactivate with the correct password
    Then the response status should be 200 or 204

  @security @P0 @TC-ACC-011
  Scenario: Deactivate account without auth token returns 401
    Given I am not authenticated
    When I POST to /v1/users/me/deactivate with the correct password but no Bearer token
    Then the response status should be 401

  @negative @P1 @TC-ACC-012
  Scenario: Deactivate account with wrong password returns 400 or 401
    Given I am logged in as the deactivate_user
    When I POST to /v1/users/me/deactivate with password "WrongPassword999!"
    Then the response status should be 400, 401, or 422

  @negative @P1 @TC-ACC-013
  Scenario: Deactivate account with missing password field returns 400 or 422
    Given I am logged in as the deactivate_user
    When I POST to /v1/users/me/deactivate with an empty request body
    Then the response status should be 400 or 422
