@customer_portal @auto
Feature: Workspace Members

  Scenario: Verify add, resend invite, and remove workspace member
    Given I am authenticated as admin
    When I add workspace members by org member
    Then the workspace members add response should be successful
    When I resend a workspace member invite
    Then the workspace member resend-invite response should be successful
    When I remove the added workspace members
    Then the workspace members remove added response should be successful
