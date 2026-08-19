@core @auto
Feature: User workspaces

  Scenario Outline: Verify the access token retrieves current workspace membership for <role>
    Given I am authenticated as user role "<role>"
    When I list my user workspaces
    And I select a user workspace from my list response
    And I get the selected user workspace membership
    Then the selected user workspace membership response should be successful
    Examples:
      | role   |
      | admin  |
      | member |
