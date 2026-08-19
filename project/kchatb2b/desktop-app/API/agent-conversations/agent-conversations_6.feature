@core @auto
Feature: Agent conversations

  Scenario: Verify the endpoint lists citations for an agent-conversation message
    Given I am authenticated as user role "admin"
    When I list my user workspaces
    And I select a user workspace from my list response
    And I list agent conversations in the selected user workspace
    And I select an agent conversation from the list response
    And I list messages in the selected agent conversation
    And I select a message from the selected agent conversation
    And I list citations for the selected agent-conversation message
    Then the selected agent-conversation message citations response should be successful
