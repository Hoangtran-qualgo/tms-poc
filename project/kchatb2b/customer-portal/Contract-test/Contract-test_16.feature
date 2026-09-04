@customer_portal @auto
Feature: Organization contracts

  Scenario: Verify get organization detail outside current-user memberships - GET 403
    Given I am authenticated as admin
    When I list Int organizations
    And I list organizations
    And I select an Int organization I do not belong to
    And I get detail of the selected non-member organization
    Then the organization detail response matches the forbidden contract
