@customer_portal @auto
Feature: Workspace Business Roles

  Scenario: Verify assign and remove members from a business role
    Given I am authenticated as admin
    When I list business roles
    And I select a listed business role with an unassigned workspace member
    And I assign members to the selected business role
    And I list selected business role members
    Then the business role assign members response should be successful
    When I remove assigned members from the selected business role
    Then the business role remove assigned member response should be successful
    When I list selected business role members
    Then the selected business role members should preserve the baseline
