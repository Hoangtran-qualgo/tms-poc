@core @auto
Feature: Agent conversations

  Scenario: Verify the endpoint retrieves an agent conversation
    Given I am authenticated as user role "admin"
    When I list my user workspaces
    And I select a user workspace from my list response
    And I list agent conversations in the selected user workspace
    And I select an agent conversation from the list response
    And I get the selected agent conversation details
    Then the selected agent conversation details response should be successful
