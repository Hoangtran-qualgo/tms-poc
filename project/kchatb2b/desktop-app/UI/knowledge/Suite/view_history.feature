Feature: user can view the version history of knowledge suite

  Background:
    Given I login desktop app as user

  Scenario Outline: user can view the version history of knowledge suite
    Given I open the dekstop app
    When I edit 1 <content> in knowledge content
    And I click on History button
    Then I can see <content> history list
    Examples:
      | content |
      | page    |
      | slide   |
