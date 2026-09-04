@customer_portal @auto
Feature: Organization contracts

  Scenario: Verify delete organization outside current-user memberships - DELETE 403
    Given I am authenticated as admin
    When I list Int organizations
    And I list organizations
    And I select an Int organization I do not belong to
    And I delete the selected non-member organization
    Then the organization delete response matches the forbidden contract
