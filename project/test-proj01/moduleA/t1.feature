@feature-tag1 @f-tag2
Feature: Test the import feature of TMS tool

  @sce-t01
  Scenario: GET response 200 - /something/{somewhere}/someone
    Given I am authenticated as admin
    When I list something of some one to somewhere
      | data | value |
      | 112  | 332   |
      | 213  | 423   |
    Then the agent conversations list response matches the success contract
