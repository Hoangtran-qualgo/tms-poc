@customer_portal @auto
Feature: Workspaces

  Scenario: Verify retrieve a non-existent workspace detail
    Given I am authenticated as admin
    When I get detail of a non-existent workspace
    Then the workspace detail response should be not found
