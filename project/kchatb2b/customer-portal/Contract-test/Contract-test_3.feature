@customer_portal @auto
Feature: Organization contracts

  Scenario: Verify list organizations rejects an invalid since ID - GET 400
    Given I am authenticated as admin
    When I list organizations with an invalid since ID
    Then the organizations list response matches the bad request contract
