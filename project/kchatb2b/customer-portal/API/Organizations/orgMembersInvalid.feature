@customer_portal @auto
Feature: Organization Members

  Scenario: Verify list organization members with an invalid query
    Given I am authenticated as admin
    When I list organization members with an invalid query
    Then the organization members list response should be a bad request
