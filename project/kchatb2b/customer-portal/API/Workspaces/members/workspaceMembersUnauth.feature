@customer_portal @auto
Feature: Workspace Members

  Scenario: Verify count workspace members without authorization
    When I count workspace members without authorization
    Then the workspace members count response should be unauthorized
