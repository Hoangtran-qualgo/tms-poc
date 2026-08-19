@customer_portal @auto
Feature: Workspaces

  Scenario: Verify retrieve workspaces list
    Given I am authenticated as admin
    When I list workspaces
    Then the workspaces list response should be successful
