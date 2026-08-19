@customer_portal @auto
Feature: Workspace Business Roles

  Scenario: Verify CRUD a business role
    Given I am authenticated as admin
    When I create a new business role
    Then the business role response should be created successfully
    When I get the created business role
    Then the business role response should be retrieved successfully
    When I update the created business role with valid info
    Then the business role response should be updated successfully
    When I delete the created business role
    Then the created business role response should be deleted successfully
