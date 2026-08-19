@customer_portal @auto
Feature: Organizations

  Scenario: Verify retrieve a non-existent organization detail
    Given I am authenticated as admin
    When I get detail of a non-existent organization
    Then the organization detail response should be not found
