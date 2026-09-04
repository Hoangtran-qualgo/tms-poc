@customer_portal @auto
Feature: Organization contracts

  Scenario: Verify get organization detail of a non-existent organization - GET 404
    Given I am authenticated as admin
    When I get detail of a non-existent organization
    Then the organization detail response matches the not-found contract
