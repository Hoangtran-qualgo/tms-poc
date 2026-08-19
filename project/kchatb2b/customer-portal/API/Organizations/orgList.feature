@customer_portal @auto
Feature: Organizations

  Scenario: Verify retrieve organizations list
    Given I am authenticated as admin
    When I list organizations
    Then the organizations list response should be successful
