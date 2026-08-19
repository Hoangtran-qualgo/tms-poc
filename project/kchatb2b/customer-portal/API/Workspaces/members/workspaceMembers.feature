@customer_portal @auto
Feature: Workspace Members

  Scenario: Verify list workspace members
    Given I am authenticated as admin
    When I list workspace members
    Then the workspace members list response should be successful
