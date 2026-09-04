@customer_portal @auto
Feature: Organization contracts

  Scenario: Verify list organizations unauthorized contract - GET 401
    When I list organizations without authorization
    Then the organizations list response matches the unauthorized contract
