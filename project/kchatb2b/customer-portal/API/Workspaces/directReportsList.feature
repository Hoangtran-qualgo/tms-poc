@customer_portal @auto
Feature: Workspace Members

  Scenario: Verify list direct reports
    Given I am authenticated as admin
    When I list direct reports of a workspace member
    Then the direct reports list response should be successful
