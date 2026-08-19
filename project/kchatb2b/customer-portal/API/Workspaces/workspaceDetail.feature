@customer_portal @auto
Feature: Workspaces

  Scenario: Verify retrieve a workspace detail
    Given I am authenticated as admin
    When I get detail of the pro workspace
    Then the workspace detail response should be successful
