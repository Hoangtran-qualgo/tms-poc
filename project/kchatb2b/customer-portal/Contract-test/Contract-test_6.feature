@customer_portal @auto
Feature: Organization contracts

  Scenario: Verify create organization unauthorized contract - POST 401
    When I create a new organization without authorization
    Then the organization create response matches the unauthorized contract
