@customer_portal @auto
Feature: Organization Members

  Scenario Outline: Verify add, update role and remove organization single member
    Given I am authenticated as admin
    When I add organization member with 1 members and <role> role
    Then the organization member add response should contain the added members successful
    When I update the added member name to new name
    Then the organization member role update response should be successful
    When I remove the added member
    Then the organization member remove response should be successful
    Examples:
      | case           | role   |
      | add new member | member |
