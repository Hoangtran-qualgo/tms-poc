# enum.components: user_manager
# enum.sprint: maintaince
Feature: test case 2

  @test @regression
  Scenario Outline:
    Given I not login
      | col1 | col2 |
      | ewq  | zasd |
    When I see login form
    Examples:
      | col1 | col2 |
      | 1    | 2    |
      | 3    | 4    |
