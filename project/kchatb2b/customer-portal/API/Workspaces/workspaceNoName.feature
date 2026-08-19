@customer_portal @auto
Feature: Workspaces

  Scenario: Verify create a workspace with empty name
    Given I am authenticated as admin
    When I create a new workspace with empty name
    Then the workspace create response should be a bad request
