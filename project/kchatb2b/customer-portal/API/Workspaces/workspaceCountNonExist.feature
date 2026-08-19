@customer_portal @auto
Feature: Workspaces

  Scenario: Verify retrieve workspaces count with a non-existent organization query
    Given I am authenticated as admin
    When I get workspaces count with a non-existent organization query
    Then the workspaces count response should be not found
