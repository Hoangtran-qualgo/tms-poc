@customer_portal @auto
Feature: Organization Members

  Scenario: Verify list organization members
    Given I am authenticated as admin
    When I list organization members
    Then the organization members list response should be successful
