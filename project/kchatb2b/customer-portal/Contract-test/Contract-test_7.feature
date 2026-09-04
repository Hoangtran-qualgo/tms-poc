@customer_portal @auto
Feature: Organization contracts

  Scenario: Verify create organization rejects an empty name - POST 400
    Given I am authenticated as admin
    When I create a new organization with empty name
    Then the organization create response matches the empty-name bad request contract
