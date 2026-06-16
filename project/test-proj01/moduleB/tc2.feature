@feature-tag1 @f-tag2
Feature: Test the import feature of TMS tool

  @sc-t02
  Scenario Outline: GET response 401 - <key> - /something/{somewhere}/someone
    When I list agent conversations without authorization <val>
    Then the  something of some one to somewhere response matches the unauthorized contract
    Examples:
      | key | val |
      | k1  | v1  |
