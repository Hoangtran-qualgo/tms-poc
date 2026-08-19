@customer_portal @auto
Feature: Workspaces

  Scenario: Verify CUD a workspace
    Given I am authenticated as owner
    When I create a new workspace
    Then the workspace response should be created successfully
    When I update the created workspace with valid info
    Then the workspace response should be updated successfully
    When I delete the created workspace
    Then the created workspace response should be deleted successfully
