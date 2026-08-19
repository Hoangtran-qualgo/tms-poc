@customer_portal @auto
Feature: Workspace Business Roles

  Scenario: Verify retrieve business roles list
    Given I am authenticated as admin
    When I list business roles
    Then the business roles list response should be successful
