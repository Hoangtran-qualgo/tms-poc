@customer_portal @auto
Feature: Organization contracts

  Scenario: Verify delete of a non-existent organization - DELETE 404
    Given I am authenticated as admin
    When I delete a non-existent organization
    Then the organization delete response matches the not-found contract
