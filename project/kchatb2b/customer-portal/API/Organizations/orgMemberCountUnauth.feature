@customer_portal @auto
Feature: Organization Members

  Scenario: Verify count organization members without authorization
    When I count organization members without authorization
    Then the organization members count response should be unauthorized
