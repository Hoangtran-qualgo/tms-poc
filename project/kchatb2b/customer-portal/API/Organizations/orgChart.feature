@customer_portal @auto
Feature: Workspace Members

  Scenario: Verify retrieve org chart
    Given I am authenticated as admin
    When I retrieve the org chart
    Then the org chart response should be successful
