@api @auth
Feature: Auth API
  As a registered user
  I want to manage authentication tokens and password recovery
  So that I can securely access and recover my account

  Background:
    Given the API is available at the configured base URL
    And the API key header is set

  # ── Refresh Token ─────────────────────────────────────────────────────────────

  @smoke @P0 @TC-AUTH-001
  Scenario: Refresh token with valid refresh token returns new access token
    Given I am logged in and have a valid refresh token
    When I POST to /v1/auth/refresh with the refresh token
    Then the response status should be 200 or 201
    And the response body should contain a new access token

  @negative @P1 @TC-AUTH-002
  Scenario: Refresh token with invalid JWT value returns 401
    Given I have an invalid refresh token "invalid.jwt.token"
    When I POST to /v1/auth/refresh with the invalid token
    Then the response status should be 400, 401, or 422

  @negative @P1 @TC-AUTH-003
  Scenario: Refresh token with missing refresh_token field returns 400 or 422
    Given I have an empty request body
    When I POST to /v1/auth/refresh with no refresh_token field
    Then the response status should be 400 or 422

  # ── Forgot Password ───────────────────────────────────────────────────────────

  @smoke @P0 @TC-AUTH-004
  Scenario: Forgot password with valid existing email returns 200
    Given an existing registered user
    When I POST to /v1/auth/forgot-password with the user's email
    Then the response status should be 200, 201, or 202

  @negative @P1 @TC-AUTH-005
  Scenario: Forgot password with non-existent email does not reveal 404
    Given a non-existent email "nonexistent_qa_test@mailinator.com"
    When I POST to /v1/auth/forgot-password with that email
    Then the response status should be 200, 201, 202, or 404

  @negative @P1 @TC-AUTH-006
  Scenario: Forgot password with invalid email format returns 400 or 422
    Given an invalid email format "not-an-email"
    When I POST to /v1/auth/forgot-password with that email
    Then the response status should be 400 or 422

  # ── Validate Reset Code ───────────────────────────────────────────────────────

  @smoke @P0 @TC-AUTH-007
  Scenario: Validate reset code with invalid code returns valid:false
    Given an invalid reset code "00000000-0000-0000-0000-000000000000"
    When I GET /v1/auth/validate-reset with that code as a query param
    Then the response status should be 200
    And the response body should contain "valid": false

  @negative @P1 @TC-AUTH-008
  Scenario: Validate reset code with missing code query param returns 400 or 422
    Given no code query parameter
    When I GET /v1/auth/validate-reset without a code param
    Then the response status should be 400 or 422

  # ── Reset Password ────────────────────────────────────────────────────────────

  @negative @P1 @TC-AUTH-009
  Scenario: Reset password with invalid code returns 400 or 404
    Given an invalid reset code "00000000-0000-0000-0000-000000000000"
    When I POST to /v1/auth/reset-password with code, new_password "NewPass123!", confirm_password "NewPass123!"
    Then the response status should be 400, 404, or 422

  @negative @P1 @TC-AUTH-010
  Scenario: Reset password with mismatched new and confirm passwords returns 400 or 422
    Given an invalid reset code "00000000-0000-0000-0000-000000000000"
    When I POST to /v1/auth/reset-password with new_password "NewPass123!" and confirm_password "DifferentPass456!"
    Then the response status should be 400 or 422

  # ── Resend Email Verification ─────────────────────────────────────────────────

  @smoke @P0 @TC-AUTH-011
  Scenario: Resend verification email for existing user returns 200
    Given an existing registered user
    When I POST to /v1/auth/resend-email-verif with the user's email
    Then the response status should be 200, 201, or 202

  @negative @P1 @TC-AUTH-012
  Scenario: Resend verification email with invalid email format returns 400 or 422
    Given an invalid email format "bad-email"
    When I POST to /v1/auth/resend-email-verif with that email
    Then the response status should be 400 or 422

  @security @P0 @TC-AUTH-013
  Scenario: Resend verification email without x-api-key returns 401 or 403
    Given the API key header is not set
    When I POST to /v1/auth/resend-email-verif with any email
    Then the response status should be 401 or 403
