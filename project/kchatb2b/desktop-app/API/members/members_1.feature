@core @auto
Feature: Workspace members

  Scenario: Verify the access token resolves a workspace member
    Given I am authenticated as user role "admin"
    When I list my user workspaces
    And I select a user workspace from my list response
    And I list members of the selected user workspace
    And I select a workspace member from my list response
    And I resolve the user cards of the selected workspace member
    Then the selected workspace member user cards resolve response should be successful
