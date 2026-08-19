@core @auto
Feature: Knowledge templates

  @pending
  Scenario: Verify the endpoint retrieves an owned knowledge template
    Given I am authenticated as user role "admin"
    When I list knowledge templates created by the authenticated member
    And I select a knowledge template from the created-template list
    And I get the selected template created by the authenticated member
    Then the created-template list response should be successful
    And the selected created-template response should be successful
