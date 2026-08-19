@customer_portal @auto
Feature: Space Conversations

  Scenario: Verify retrieve a listed conversation
    Given I am authenticated as admin
    When I list spaces
    And I select the first listed space
    And I list conversations of the selected space
    And I select the first listed conversation
    And I get the selected conversation
    Then the selected conversation response should be successful
