@customer_portal @auto
Feature: Workspace Members

  Scenario: Verify get member HR profile
    Given I am authenticated as admin
    When I get a workspace member HR profile
    Then the member HR profile response should be successful
