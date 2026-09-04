@customer_portal @auto
Feature: Organization contracts

  Scenario: Verify get organization detail unauthorized contract - GET 401
    When I get detail of the existing organization without authorization
    Then the organization detail response matches the unauthorized contract
