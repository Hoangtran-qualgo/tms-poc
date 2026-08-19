@core @auto
Feature: Knowledge templates

  @pending
  Scenario: Verify the published knowledge-template lifecycle
    Given I am authenticated as user role "admin"
    When I create a knowledge template in the configured workspace
    Then the knowledge-template create response should be successful
    When I retrieve the created draft template
    Then the created draft template should match the create request
    When I add a paragraph section to the created knowledge template
    Then the knowledge-template sections response should be successful
    When I retrieve the created draft template
    Then the created draft template should contain the added section
    When I publish the created knowledge template
    Then the knowledge-template publish response should be successful
    When I retrieve the published knowledge template
    Then the published knowledge-template response should be successful
    When I update the published knowledge template
    Then the knowledge-template update response should be successful
    When I retrieve the updated knowledge template
    Then the updated knowledge-template response should be successful
    When I delete the created knowledge template
    Then the created knowledge-template response should be deleted successfully
