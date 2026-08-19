@customer_portal @auto
Feature: Organizations

  Scenario: Verify retrieve organizations count
    Given I am authenticated as admin
    When I get organizations count
    Then the organizations count response should be successful
