@customer_portal @auto
Feature: Workspace Members

  Scenario: Verify list suggested members with an invalid query
    Given I am authenticated as admin
    When I list suggested members with an invalid query
    Then the suggested members list response should be a bad request
