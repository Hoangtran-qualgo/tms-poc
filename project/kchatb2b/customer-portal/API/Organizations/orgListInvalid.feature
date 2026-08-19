@customer_portal @auto
Feature: Organizations

  Scenario: Verify retrieve organizations list with an invalid query
    Given I am authenticated as admin
    When I list organizations with an invalid query
    Then the organizations list response should be a bad request
