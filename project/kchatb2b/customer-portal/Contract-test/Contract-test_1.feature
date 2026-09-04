@customer_portal @auto
Feature: Organization contracts

  Scenario: Verify list organizations success contract - GET 200
    Given I am authenticated as admin
    When I list organizations
    Then the organizations list response matches the success contract
