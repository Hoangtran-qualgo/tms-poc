@core @auto
Feature: User workspaces

  Scenario Outline: Verify the access token lists user workspaces for <role>
    Given I am authenticated as user role "<role>"
    When I list my user workspaces
    Then the user workspaces response should be successful
    Examples:
      | role   |
      | admin  |
      | member |
