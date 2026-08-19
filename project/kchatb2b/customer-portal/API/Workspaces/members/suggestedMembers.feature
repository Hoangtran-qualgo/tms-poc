@customer_portal @auto
Feature: Workspace Members

  Scenario: Verify list suggested members
    Given I am authenticated as admin
    When I list suggested members
    Then the suggested members list response should be successful
