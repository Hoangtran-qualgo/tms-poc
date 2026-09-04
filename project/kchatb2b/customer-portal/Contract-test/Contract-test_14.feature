@customer_portal @auto
Feature: Organization contracts

  Scenario: Verify get organization detail rejects an invalid ID - GET 400
    Given I am authenticated as admin
    When I get detail of an organization with an invalid ID
    Then the organization detail response matches the bad request contract
