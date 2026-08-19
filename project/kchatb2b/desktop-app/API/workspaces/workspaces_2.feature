@core @auto
Feature: User workspaces

  Scenario Outline: Verify the access token counts user workspaces for <role>
    Given I am authenticated as user role "<role>"
    When I list my user workspaces
    And I get my user workspaces count
    Then the user workspaces count response should be successful
    Examples:
      | role   |
      | admin  |
      | member |
