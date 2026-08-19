@core @auto
Feature: Workspace members

  Scenario: Verify email recovery authentication
    Given I am authenticated as user email "autouser01@yopmail.com"
    Then the user access token should be available
