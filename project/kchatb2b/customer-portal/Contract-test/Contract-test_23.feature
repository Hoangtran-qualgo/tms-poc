@customer_portal @auto
Feature: Organization contracts

  Scenario: Verify delete organization unauthorized contract - DELETE 401
    When I delete an organization without authorization
    Then the organization delete response matches the unauthorized contract
