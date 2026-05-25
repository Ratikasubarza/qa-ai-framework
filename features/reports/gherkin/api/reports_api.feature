@api @reports
Feature: Reports API
  As an authenticated user
  I want to submit bug or abuse reports to the platform
  So that the team can investigate and improve the product

  Background:
    Given the API is available at the configured base URL
    And the API key header is set

  # ── POST /v1/reports ──────────────────────────────────────────────────────────

  @smoke @P0 @TC-RPT-001
  Scenario: Submit valid report returns 200 or 201
    Given I am logged in as a registered user
    When I POST to /v1/reports with subject "QA automated test report", report_type "BUG", message "Automated test submission — please ignore."
    Then the response status should be 200 or 201
    And the response code should be "OK" or the data should contain an "id"

  @security @P0 @TC-RPT-002
  Scenario: Submit report without auth token returns 401
    Given I am not authenticated
    When I POST to /v1/reports with a valid report payload
    Then the response status should be 401

  @negative @P1 @TC-RPT-003
  Scenario: Submit report with invalid report_type returns 400 or 422
    Given I am logged in as a registered user
    When I POST to /v1/reports with report_type "INVALID_TYPE"
    Then the response status should be 400 or 422

  @negative @P1 @TC-RPT-004
  Scenario: Submit report with missing required fields returns 400 or 422
    Given I am logged in as a registered user
    When I POST to /v1/reports with only subject "Incomplete" and no report_type or message
    Then the response status should be 400 or 422
