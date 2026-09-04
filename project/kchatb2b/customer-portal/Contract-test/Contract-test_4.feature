@customer_portal @auto
Feature: Organization contracts

  Scenario: Verify list organizations returns no result for a non-existent name - GET 200
    Given I am authenticated as admin
    When I search organizations with a non-existent name
    Then the organizations search response should be empty and match the success contract
