@customer_portal @auto
Feature: Workspace Departments

  Scenario: Verify retrieve departments list
    Given I am authenticated as admin
    When I list departments
    Then the departments list response should be successful
