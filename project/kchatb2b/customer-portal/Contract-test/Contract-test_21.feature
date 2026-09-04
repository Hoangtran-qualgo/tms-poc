@customer_portal @auto
Feature: Organization contracts

  Scenario: Verify update organization outside current-user memberships - PATCH 403
    Given I am authenticated as admin
    When I list Int organizations
    And I list organizations
    And I select an Int organization I do not belong to
    And I update the selected non-member organization
    Then the organization update response matches the forbidden contract
