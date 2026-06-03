Feature: create new workspace

  Background:
    Given Login as authen admin

  @test
  Scenario Outline:
    When I send api request to create new workspace
      | authen      | body                      |
      | valid token | {"name": "new workspace"} |
    Then New space created successfully
    And response return status 201
    Examples:
      | user   | pwd      |
      | admin1 | admin123 |
