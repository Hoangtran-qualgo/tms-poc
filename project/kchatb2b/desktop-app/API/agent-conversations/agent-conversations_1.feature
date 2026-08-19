@core @auto
Feature: Agent conversations

  Scenario: Verify the endpoint lists and counts agent conversations
    Given I am authenticated as user role "admin"
    When I list my user workspaces
    And I select a user workspace from my list response
    And I list agent conversations in the selected user workspace
    And I get the selected user workspace agent-conversations count
    Then the selected user workspace agent-conversations response should be successful
    And the selected user workspace agent-conversations count response should be successful
