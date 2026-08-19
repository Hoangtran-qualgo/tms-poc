@customer_portal @auto
Feature: Workspace Spaces

  Scenario: Verify retrieve an existing space
    Given I am authenticated as admin
    When I list spaces
    And I select the first listed space
    And I get the selected space
    Then the selected space response should be successful
