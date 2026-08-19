@customer_portal @auto
Feature: Space Conversations

  Scenario: Verify retrieve conversations count
    Given I am authenticated as admin
    When I list spaces
    And I select the first listed space
    And I list conversations of the selected space
    And I count conversations of the selected space
    Then the conversations count response should be successful
