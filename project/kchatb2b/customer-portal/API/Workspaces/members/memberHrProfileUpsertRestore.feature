@customer_portal @auto
Feature: Workspace Members

  Scenario: Verify upsert and restore member HR profile
    Given I am authenticated as admin
    When I upsert a workspace member HR profile
    Then the member HR profile upsert response should be successful
    When I restore the workspace member HR profile
    Then the member HR profile restore response should be successful
