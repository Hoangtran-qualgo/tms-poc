@customer_portal @auto
Feature: Space Conversations

  Scenario: Verify retrieve conversations list
    Given I am authenticated as admin
    When I list spaces
    And I select the first listed space
    And I list conversations of the selected space
    Then the conversations list response should be successful
