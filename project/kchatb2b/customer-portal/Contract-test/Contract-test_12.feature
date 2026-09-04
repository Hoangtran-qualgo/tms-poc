@customer_portal @auto
Feature: Organization contracts

  Scenario: Verify get organization detail success contract - GET 200
    Given I am authenticated as admin
    When I get detail of the existing organization
    Then the organization detail response matches the success contract
