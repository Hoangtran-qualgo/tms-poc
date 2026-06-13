# enum.components: user_manager
# enum.sprint: maintaince
@regression @test @regr
Feature: test case 2

  @test @regression
  Scenario Outline: test case 2
    Given I not login
      | col1 | col2 |
      | ewq  | zasd |
    When I see login form
    Examples:
      | col1 | col2 |
      | 1    | 2    |
      | 3    | 4    |
