@customer_portal @auto
Feature: Workspace Members

  Scenario: Verify list workspace members with an invalid query
    Given I am authenticated as admin
    When I list workspace members with an invalid query
    Then the workspace members list response should be a bad request
