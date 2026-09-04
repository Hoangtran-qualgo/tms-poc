@customer_portal @auto
Feature: Organization contracts

  Scenario: Verify organizations count for a non-existent name - GET 200
    Given I am authenticated as admin
    When I get organizations count for a non-existent name
    Then the organizations count response should be zero and match the success contract
