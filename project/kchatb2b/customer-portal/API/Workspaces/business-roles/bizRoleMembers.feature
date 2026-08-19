@customer_portal @auto
Feature: Workspace Business Roles

  Scenario: Verify list business role members
    Given I am authenticated as admin
    When I list business roles
    And I select a listed business role
    And I list selected business role members
    Then the business role members list response should be successful
