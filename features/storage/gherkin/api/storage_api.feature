@api @storage
Feature: Storage API
  As an authenticated user
  I want to retrieve presigned URLs for stored objects
  So that I can access media files from cloud storage

  Background:
    Given the API is available at the configured base URL
    And the API key header is set

  # ── GET /v1/storage/presign/:key ─────────────────────────────────────────────

  @smoke @P0 @TC-STR-001
  Scenario: Get presigned URL with valid key path format returns 200 or 404
    Given I am logged in as a registered user
    When I GET /v1/storage/presign/profiles/00000000-0000-0000-0000-000000000000/sample.jpg with a valid Bearer token
    Then the response status should be 200 or 404
    And if status is 200 the response data should contain a "url" field

  @security @P0 @TC-STR-002
  Scenario: Get presigned URL without auth token returns 401
    Given I am not authenticated
    When I GET /v1/storage/presign/profiles/00000000-0000-0000-0000-000000000000/sample.jpg without a Bearer token
    Then the response status should be 401

  @P1 @TC-STR-003
  Scenario: Presign URL response always contains a code field
    Given I am logged in as a registered user
    When I GET /v1/storage/presign/profiles/00000000-0000-0000-0000-000000000000/sample.jpg with a valid Bearer token
    Then the response status should be 200 or 404
    And the response body should contain a "code" field
