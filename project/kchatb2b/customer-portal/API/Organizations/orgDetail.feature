@customer_portal @auto
Feature: Organizations

  Scenario: Verify retrieve a organization detail
    Given I am authenticated as admin
    When I get detail of the existing organization
    Then the organization detail response should be successful
