@customer_portal @auto
Feature: Workspace Members

  Scenario: Verify list suggested members without authorization
    When I list suggested members without authorization
    Then the suggested members list response should be unauthorized
