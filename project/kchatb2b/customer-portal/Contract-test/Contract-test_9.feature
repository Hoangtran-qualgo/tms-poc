@customer_portal @auto
Feature: Organization contracts

  Scenario: Verify organizations count success contract - GET 200
    Given I am authenticated as admin
    When I get organizations count
    Then the organizations count response matches the success contract
