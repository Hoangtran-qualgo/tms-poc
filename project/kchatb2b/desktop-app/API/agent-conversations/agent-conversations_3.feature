@core @auto
Feature: Agent conversations

  Scenario: Verify the endpoint lists messages in an agent conversation
    Given I am authenticated as user role "admin"
    When I list my user workspaces
    And I select a user workspace from my list response
    And I list agent conversations in the selected user workspace
    And I select an agent conversation from the list response
    And I list messages in the selected agent conversation
    Then the selected agent conversation messages response should be successful
