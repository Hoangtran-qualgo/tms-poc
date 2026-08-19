@core @auto
Feature: Knowledge templates

  Scenario: Verify the endpoint lists knowledge template categories
    Given I am authenticated as user role "admin"
    When I list knowledge template categories in the configured workspace
    Then the knowledge-template categories response should be successful
