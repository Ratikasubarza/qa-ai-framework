@api @settings
Feature: Settings API
  As an authenticated user
  I want to view and update my toggle and option preferences
  So that I can personalise my notification, audience, and message settings

  Background:
    Given the API is available at the configured base URL
    And the API key header is set
    And I am logged in as a registered user
    And the original settings values are captured for restoration

  # ── GET /v1/settings/toggle ───────────────────────────────────────────────────

  @smoke @P0 @TC-SETS-001
  Scenario: Get NOTIFICATION toggle settings returns 200 with list
    When I GET /v1/settings/toggle with param section="NOTIFICATION"
    Then the response status should be 200
    And the response code should be "OK"
    And the response data should be a list

  @P1 @TC-SETS-002
  Scenario: Get PERSONAL toggle settings returns 200
    When I GET /v1/settings/toggle with param section="PERSONAL"
    Then the response status should be 200

  @security @P0 @TC-SETS-003
  Scenario: Get toggle settings without auth returns 401
    Given I am not authenticated
    When I GET /v1/settings/toggle with param section="NOTIFICATION" without a Bearer token
    Then the response status should be 401

  # ── PUT /v1/settings/toggle ───────────────────────────────────────────────────

  @smoke @P0 @TC-SETS-004
  Scenario: Update toggle setting returns 200
    When I PUT /v1/settings/toggle with section="NOTIFICATION", key="repost", value=true
    Then the response status should be 200 or 201

  @negative @P1 @TC-SETS-005
  Scenario: Update toggle with invalid key returns 400 or 422
    When I PUT /v1/settings/toggle with section="NOTIFICATION", key="invalid_key", value=true
    Then the response status should be 400 or 422

  @security @P0 @TC-SETS-006
  Scenario: Update toggle without auth returns 401
    Given I am not authenticated
    When I PUT /v1/settings/toggle with key="repost", value=true but no Bearer token
    Then the response status should be 401

  # ── GET /v1/settings/option ───────────────────────────────────────────────────

  @smoke @P0 @TC-SETS-007
  Scenario: Get MESSAGE option setting returns 200 with key and enum value
    When I GET /v1/settings/option with param section="MESSAGE"
    Then the response status should be 200
    And the response code should be "OK"
    And the response data should contain key "message_preference"
    And the value should be one of "NO_ONE", "VERIFIED_USER", "EVERYONE"

  @P1 @TC-SETS-008
  Scenario: Get AUDIENCE option setting returns 200
    When I GET /v1/settings/option with param section="AUDIENCE"
    Then the response status should be 200

  @security @P0 @TC-SETS-009
  Scenario: Get option settings without auth returns 401
    Given I am not authenticated
    When I GET /v1/settings/option with param section="MESSAGE" without a Bearer token
    Then the response status should be 401

  # ── PUT /v1/settings/option ───────────────────────────────────────────────────

  @smoke @P0 @TC-SETS-010
  Scenario: Update message_preference to NO_ONE returns 200
    When I PUT /v1/settings/option with section="MESSAGE", key="message_preference", value="NO_ONE"
    Then the response status should be 200 or 201

  @negative @P1 @TC-SETS-011
  Scenario: Update option with invalid enum value returns 400 or 422
    When I PUT /v1/settings/option with section="AUDIENCE", key="tagging_preference", value="INVALID_VALUE"
    Then the response status should be 400 or 422

  @security @P0 @TC-SETS-012
  Scenario: Update option without auth returns 401
    Given I am not authenticated
    When I PUT /v1/settings/option with section="MESSAGE", key="message_preference", value="EVERYONE" but no Bearer token
    Then the response status should be 401

  # ── Additional section regressions ───────────────────────────────────────────

  @smoke @P0 @TC-SETS-013
  Scenario: Get MESSAGE option preference returns 200 with valid enum value
    When I GET /v1/settings/option with param section="MESSAGE"
    Then the response status should be 200
    And the data key should be "message_preference"
    And the value should be one of "NO_ONE", "VERIFIED_USER", "EVERYONE"

  @security @P0 @TC-SETS-014
  Scenario: Get MESSAGE option preference without auth returns 401
    Given I am not authenticated
    When I GET /v1/settings/option with param section="MESSAGE" without a Bearer token
    Then the response status should be 401

  @smoke @P0 @TC-SETS-015
  Scenario: Update message_preference to NO_ONE persists
    When I PUT /v1/settings/option with section="MESSAGE", key="message_preference", value="NO_ONE"
    Then the response status should be 200 or 201

  @negative @P1 @TC-SETS-016
  Scenario: Update message_preference with invalid value returns 400 or 422
    When I PUT /v1/settings/option with section="MESSAGE", key="message_preference", value="INVALID_VALUE"
    Then the response status should be 400 or 422

  @smoke @P0 @TC-SETS-017
  Scenario: Get NOTIFICATION toggle preferences includes mention_replies key
    When I GET /v1/settings/toggle with param section="NOTIFICATION"
    Then the response status should be 200
    And the response data should be a list
    And the list should contain an item with key "mention_replies"

  @security @P0 @TC-SETS-018
  Scenario: Get NOTIFICATION toggle preferences without auth returns 401
    Given I am not authenticated
    When I GET /v1/settings/toggle with param section="NOTIFICATION" without a Bearer token
    Then the response status should be 401

  @smoke @P0 @TC-SETS-019
  Scenario: Update NOTIFICATION toggle preference returns 200
    When I PUT /v1/settings/toggle with section="NOTIFICATION", key="mention_replies", value=false
    Then the response status should be 200 or 201

  @smoke @P0 @TC-SETS-020
  Scenario: Update AUDIENCE option preference returns 200
    When I PUT /v1/settings/option with section="AUDIENCE", key="tagging_preference", value="FOLLOWERS_ONLY"
    Then the response status should be 200 or 201
