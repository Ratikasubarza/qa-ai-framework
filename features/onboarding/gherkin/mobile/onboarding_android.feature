@mobile @android @onboarding
Feature: Onboarding Android — app.thehono.development
  As a newly approved Hono user
  I want to complete my profile onboarding
  So that I can access the Hono community feed

  Background:
    Given a new approved user account has been created via API and DB setup
    And the Hono Android app is launched
    And the user logs in for the first time
    Then the onboarding screen "Welcome to HONO!" should be displayed

  @smoke @P0 @TC-MOB-ONB-001
  Scenario: Complete full onboarding flow reaches feed screen
    When I tap "Let's personalize profile"
    And I fill my full name and tap Continue
    And I fill my current role and company and tap Continue
    And I select Indonesia as country and Jakarta Pusat as city and tap Continue
    And I select 2 industries from the modal and tap Continue
    And I select 2 business areas and tap Continue
    And I select 2 personal interests and tap Continue
    And I select 2 social causes and tap Submit
    And I tap "Skip & Continue" on add profile picture screen
    And I tap "Go to homepage" on congratulations screen
    Then I should see the feed screen with Home tab visible

  @functional @P1 @TC-MOB-ONB-002
  Scenario: New approved user sees onboarding on first login
    Given a newly approved user has never completed onboarding
    When the user logs in for the first time
    Then the "Welcome to HONO!" onboarding screen should appear
    And the "Let's personalize profile" button should be visible

  @functional @P1 @TC-MOB-ONB-003
  Scenario: User can skip profile picture during onboarding
    When I complete all onboarding steps up to add profile picture
    And I tap "Skip & Continue" instead of adding a picture
    And I tap "Go to homepage"
    Then I should reach the feed screen successfully
    And onboarding_completed_at should be set in the database
