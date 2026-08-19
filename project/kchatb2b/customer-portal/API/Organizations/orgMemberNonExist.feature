@customer_portal @auto
Feature: Organization Members

  Scenario: Verify count organization members of a non-existent organization
    Given I am authenticated as admin
    When I count organization members of a non-existent organization
    Then the organization members count response should be not found
