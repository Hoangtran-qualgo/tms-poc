@customer_portal @auto
Feature: Workspace Departments

  Scenario: Verify CRUD a department
    Given I am authenticated as admin
    When I create a new department
    Then the department response should be created successfully
    When I get the created department
    Then the department response should be retrieved successfully
    When I update the created department with valid info
    Then the department response should be updated successfully
    When I delete the created department
    Then the created department response should be deleted successfully
