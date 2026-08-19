@customer_portal @auto
Feature: Workspaces

  Scenario: Verify retrieve workspaces count
    Given I am authenticated as admin
    When I get workspaces count
    Then the workspaces count response should be successful
