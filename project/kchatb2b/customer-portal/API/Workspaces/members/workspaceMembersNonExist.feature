@customer_portal @auto
Feature: Workspace Members

  Scenario: Verify count workspace members of a non-existent workspace
    Given I am authenticated as admin
    When I count workspace members of a non-existent workspace
    Then the workspace members count response should be not found
