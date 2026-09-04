@customer_portal @auto
Feature: Organization contracts

  Scenario: Verify update organization rejects an invalid ID - PATCH 400
    Given I am authenticated as admin
    When I update an organization with an invalid ID
    Then the organization update response matches the bad request contract
