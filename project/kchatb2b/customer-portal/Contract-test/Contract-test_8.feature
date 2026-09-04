@customer_portal @auto
Feature: Organization contracts

  Scenario: Verify create organization rejects a missing name - POST 400
    Given I am authenticated as admin
    When I create a new organization without name
    Then the organization create response matches the missing-name bad request contract
