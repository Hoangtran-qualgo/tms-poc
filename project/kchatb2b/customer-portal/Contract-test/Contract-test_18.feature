@customer_portal @auto
Feature: Organization contracts

  Scenario: Verify update organization unauthorized contract - PATCH 401
    When I update an organization without authorization
    Then the organization update response matches the unauthorized contract
