@core @auto
Feature: Workspace members

  Scenario Outline: Verify the access token lists and counts workspace members for <role>
    Given I am authenticated as user role "<role>"
    When I list my user workspaces
    And I select a user workspace from my list response
    And I list members of the selected user workspace
    And I get the selected user workspace members count
    Then the selected user workspace members response should be successful
    And the selected user workspace members count response should be successful
    Examples:
      | role   |
      | admin  |
      | member |
