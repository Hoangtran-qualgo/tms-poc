@customer_portal @auto
Feature: Organization Members

  Scenario Outline: Verify add and remove organization multiple members - <case>
    Given I am authenticated as admin
    When I add organization <number> members with default role
    Then the organization add member response should contain the added members successful
    When I remove all added members
    Then the organization member all remove response should be successful
    Examples:
      | case          | number |
      | add 1 member  | 1      |
      | add 3 members | 3      |
