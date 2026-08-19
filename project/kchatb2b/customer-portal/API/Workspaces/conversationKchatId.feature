@customer_portal @auto
Feature: Space Conversations

  Scenario: Verify retrieve a conversation by KChat id
    Given I am authenticated as admin
    When I list spaces
    And I select the first listed space
    And I list conversations of the selected space
    And I select the first listed conversation
    And I get the selected conversation
    And I get the selected conversation by KChat id
    Then the KChat conversation response should be successful
