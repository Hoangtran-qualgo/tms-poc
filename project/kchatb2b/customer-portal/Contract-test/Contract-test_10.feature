@customer_portal @auto
Feature: Organization contracts

  Scenario: Verify organizations count unauthorized contract - GET 401
    When I get organizations count without authorization
    Then the organizations count response matches the unauthorized contract
