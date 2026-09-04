@customer_portal @auto
Feature: Organization contracts

  Scenario: Verify create organization success contract and cleanup - POST 201, DELETE 204
    Given I am authenticated as admin
    When I create a new organization
    Then the organization create response matches the success contract
    When I delete the created organization
    Then the created organization delete response matches the cleanup contract
