@api @user_settings
Feature: User Settings API
  As an authenticated user
  I want to manage my toggle and option preferences
  So that I can control my notification, privacy, and messaging experience on Hono

  Background:
    Given the API is available at the configured base URL
    And the API key header is set

  # ── GET /v1/settings/toggle ───────────────────────────────────────────────────

  @smoke @P0 @TC-ST-001
  Scenario: GET PERSONAL toggle settings returns 200 with show_email and show_phone keys
    Given I am logged in with valid credentials
    When I request the PERSONAL toggle settings
    Then the response status should be 200
    And the response code should be "OK"
    And the data should contain keys "show_email" and "show_phone"
    And each toggle item should have "key", "label", and a boolean "value"

  @smoke @P0 @TC-ST-002
  Scenario: GET NOTIFICATION toggle settings returns 200 with all 7 required keys
    Given I am logged in with valid credentials
    When I request the NOTIFICATION toggle settings
    Then the response status should be 200
    And the response code should be "OK"
    And the data should contain all keys: mention_replies, repost, reaction, tag, new_followers, direct_message, message_reaction

  @negative @P1 @TC-ST-003
  Scenario: GET toggle settings with invalid section returns 422
    Given I am logged in with valid credentials
    When I request toggle settings with section "INVALID_SECTION"
    Then the response status should be 422

  @negative @P1 @TC-ST-004
  Scenario: GET toggle settings with missing section param returns 422
    Given I am logged in with valid credentials
    When I request toggle settings without a section param
    Then the response status should be 422

  @negative @P0 @TC-ST-005
  Scenario: GET toggle settings without auth token returns 401
    Given the auth token is not set
    When I request the NOTIFICATION toggle settings
    Then the response status should be 401

  # ── PUT /v1/settings/toggle ───────────────────────────────────────────────────

  @smoke @P0 @TC-ST-006
  Scenario: PUT show_email=False returns 200 with OK code and Data saved message
    Given I am logged in with valid credentials
    When I update the PERSONAL toggle "show_email" to false
    Then the response status should be 200
    And the response code should be "OK"
    And the response message should contain "Data saved"

  @smoke @P0 @TC-ST-007
  Scenario: PUT mention_replies=False returns 200
    Given I am logged in with valid credentials
    When I update the NOTIFICATION toggle "mention_replies" to false
    Then the response status should be 200
    And the response code should be "OK"

  @boundary @P2 @TC-ST-008
  Scenario: PUT show_phone=False then GET verifies persistence
    Given I am logged in with valid credentials
    When I update the PERSONAL toggle "show_phone" to false
    And I request the PERSONAL toggle settings
    Then the returned value for "show_phone" should be false

  @negative @P1 @TC-ST-009
  Scenario: PUT toggle with invalid key returns 400 or 422
    Given I am logged in with valid credentials
    When I update toggle with section "NOTIFICATION" and key "invalid_key_xyz"
    Then the response status should be 400 or 422

  @negative @P1 @TC-ST-010
  Scenario: PUT toggle with string value instead of bool returns 422
    Given I am logged in with valid credentials
    When I update toggle "repost" with value "true" (string, not bool)
    Then the response status should be 422

  @negative @P1 @TC-ST-011
  Scenario: PUT toggle with missing key field returns 422
    Given I am logged in with valid credentials
    When I send a PUT toggle request with section and value but no key
    Then the response status should be 422

  @negative @P0 @TC-ST-012
  Scenario: PUT toggle without auth token returns 401
    Given the auth token is not set
    When I update a toggle setting
    Then the response status should be 401

  # ── GET /v1/settings/option ───────────────────────────────────────────────────

  @smoke @P0 @TC-ST-013
  Scenario: GET AUDIENCE option returns 200 with tagging_preference and valid enum value
    Given I am logged in with valid credentials
    When I request the AUDIENCE option settings
    Then the response status should be 200
    And the response code should be "OK"
    And the key should be "tagging_preference"
    And the value should be one of "NO_ONE", "FOLLOWERS_ONLY", "EVERYONE"

  @smoke @P0 @TC-ST-014
  Scenario: GET MESSAGE option returns 200 with message_preference and valid enum value
    Given I am logged in with valid credentials
    When I request the MESSAGE option settings
    Then the response status should be 200
    And the response code should be "OK"
    And the key should be "message_preference"
    And the value should be one of "NO_ONE", "VERIFIED_USER", "EVERYONE"

  @smoke @P0 @TC-ST-015
  Scenario: Every option item in MESSAGE section has value and label string fields
    Given I am logged in with valid credentials
    When I request the MESSAGE option settings
    Then the response status should be 200
    And each option item should have string "value" and "label" fields

  @negative @P1 @TC-ST-016
  Scenario: GET option settings with invalid section returns 422
    Given I am logged in with valid credentials
    When I request option settings with section "INVALID"
    Then the response status should be 422

  @negative @P0 @TC-ST-017
  Scenario: GET option settings without auth token returns 401
    Given the auth token is not set
    When I request the MESSAGE option settings
    Then the response status should be 401

  # ── PUT /v1/settings/option ───────────────────────────────────────────────────

  @smoke @P0 @TC-ST-018
  Scenario: PUT message_preference=NO_ONE returns 200 with OK code and Data saved message
    Given I am logged in with valid credentials
    When I update the MESSAGE option "message_preference" to "NO_ONE"
    Then the response status should be 200
    And the response code should be "OK"
    And the response message should contain "Data saved"

  @smoke @P0 @TC-ST-019
  Scenario: PUT tagging_preference=FOLLOWERS_ONLY returns 200
    Given I am logged in with valid credentials
    When I update the AUDIENCE option "tagging_preference" to "FOLLOWERS_ONLY"
    Then the response status should be 200
    And the response code should be "OK"

  @boundary @P2 @TC-ST-020
  Scenario: PUT message_preference=VERIFIED_USER then GET verifies persistence
    Given I am logged in with valid credentials
    When I update the MESSAGE option "message_preference" to "VERIFIED_USER"
    And I request the MESSAGE option settings
    Then the returned value should be "VERIFIED_USER"

  @negative @P1 @TC-ST-021
  Scenario: PUT option with invalid enum value returns 400 or 422
    Given I am logged in with valid credentials
    When I update option "tagging_preference" with value "INVALID_VALUE"
    Then the response status should be 400 or 422

  @negative @P1 @TC-ST-022
  Scenario: PUT option with invalid key returns 400 or 422
    Given I am logged in with valid credentials
    When I update option with key "invalid_key_xyz" in MESSAGE section
    Then the response status should be 400 or 422

  @negative @P1 @TC-ST-023
  Scenario: PUT option with missing section and value fields returns 422
    Given I am logged in with valid credentials
    When I send a PUT option request with only a key and no section or value
    Then the response status should be 422

  @negative @P0 @TC-ST-024
  Scenario: PUT option without auth token returns 401
    Given the auth token is not set
    When I update an option setting
    Then the response status should be 401
