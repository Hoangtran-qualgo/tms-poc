@customer_portal @auto
Feature: Workspace Members

  Scenario: Verify list suggested members of a non-existent workspace
    Given I am authenticated as admin
    When I list suggested members of a non-existent workspace
    Then the suggested members list response should be not found
