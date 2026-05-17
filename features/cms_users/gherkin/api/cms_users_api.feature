@api @cms @users
Feature: CMS Users API
  As a CMS admin
  I want to list and manage users via API
  So that I can approve, reject, or view user registrations

  Background:
    Given the API is available at the configured base URL
    And the API key header is set
    And I am authenticated as CMS admin

  @smoke @P0 @TC-CMS-USERS-001
  Scenario: List users with valid CMS token
    When I request the users list with page=1 and size=20
    Then the response status should be 200
    And the response should contain a list of users
    And each user should have id, name, email, status fields

  @security @P0 @TC-CMS-USERS-002
  Scenario: List users without token returns 401
    Given I am not authenticated
    When I request the users list
    Then the response status should be 401

  @functional @P1 @TC-CMS-USERS-003
  Scenario: Filter users by approved status
    When I request the users list with status=APPROVED filter
    Then the response status should be 200
    And all returned users should have status "APPROVED"

  @functional @P1 @TC-CMS-USERS-004
  Scenario: Pagination returns correct number of results
    When I request the users list with page=1 and size=5
    Then the response status should be 200
    And the response should contain at most 5 users

  @functional @P1 @TC-CMS-USERS-005
  Scenario: Order users by name descending
    When I request the users list with orderBy=name and order=DESC
    Then the response status should be 200

  @functional @P1 @TC-CMS-USERS-006
  Scenario Outline: Different page sizes return correct count
    When I request the users list with size=<size>
    Then the response should contain at most <size> users

    Examples: Page sizes
      | size |
      | 5    |
      | 10   |
      | 50   |

  @functional @P1 @TC-CMS-USERS-007
  Scenario Outline: Order by created_at in different directions
    When I request the users list with orderBy=created_at and order=<order>
    Then the response status should be 200

    Examples: Order directions
      | order |
      | ASC   |
      | DESC  |

  @functional @P1 @TC-CMS-USERS-008
  Scenario: Page navigation returns different users
    When I request the users list page=1 size=10
    And I request the users list page=2 size=10
    Then the two pages should have no overlapping users

  @functional @P1 @TC-CMS-USERS-009
  Scenario Outline: Filter by each status value
    When I request the users list with status=<status>
    Then the response status should be 200

    Examples: Status values
      | status |
      | 1      |
      | 2      |
      | 3      |

  @boundary @P2 @TC-CMS-USERS-010
  Scenario: No query params uses API defaults
    When I request the users list without any params
    Then the response status should be 200
    And the response should contain a list of users

  @boundary @P2 @TC-CMS-USERS-011
  Scenario: Invalid page number is handled gracefully
    When I request the users list with page=-1
    Then the response status should be 200 or 400

  @boundary @P2 @TC-CMS-USERS-012
  Scenario: Invalid order value is handled gracefully
    When I request the users list with order=INVALID
    Then the response status should be 200 or 400
