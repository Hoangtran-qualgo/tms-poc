@customer_portal @auto
Feature: Workspaces

  Scenario: Verify retrieve workspaces list with an invalid query
    Given I am authenticated as admin
    When I list workspaces with an invalid query
    Then the workspaces list response should be a bad request
