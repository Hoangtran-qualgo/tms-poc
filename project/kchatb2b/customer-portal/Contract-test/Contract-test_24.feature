@customer_portal @auto
Feature: Organization contracts

  Scenario: Verify delete organization rejects an invalid ID - DELETE 400
    Given I am authenticated as admin
    When I delete an organization with an invalid ID
    Then the organization delete response matches the bad request contract
