@customer_portal @auto
Feature: Organizations

  Scenario: Verify create a organization with empty name
    Given I am authenticated as admin
    When I create a new organization with empty name
    Then the organization create response should be a bad request
