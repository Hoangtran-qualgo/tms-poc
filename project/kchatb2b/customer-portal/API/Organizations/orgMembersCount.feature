@customer_portal @auto
Feature: Organization Members

  Scenario: Verify count organization members
    Given I am authenticated as admin
    When I count organization members
    Then the organization members count response should be successful
