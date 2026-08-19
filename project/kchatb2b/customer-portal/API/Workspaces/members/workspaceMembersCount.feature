@customer_portal @auto
Feature: Workspace Members

  Scenario: Verify count workspace members
    Given I am authenticated as admin
    When I count workspace members
    Then the workspace members count response should be successful
