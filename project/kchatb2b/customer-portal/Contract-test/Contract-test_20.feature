@customer_portal @auto
Feature: Organization contracts

  Scenario: Verify update of a non-existent organization - PATCH 404
    Given I am authenticated as admin
    When I update a non-existent organization
    Then the organization update response matches the not-found contract
