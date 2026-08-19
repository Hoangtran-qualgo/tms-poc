@customer_portal @auto
Feature: Workspaces

  Scenario: Verify retrieve departments count
    Given I am authenticated as admin
    When I get departments count
    Then the departments count response should be successful
