@customer_portal @auto
Feature: Workspace Spaces

  Scenario: Verify retrieve spaces list
    Given I am authenticated as admin
    When I list spaces
    Then the spaces list response should be successful
