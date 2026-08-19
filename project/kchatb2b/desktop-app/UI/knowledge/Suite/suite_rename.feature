Feature: 

  Scenario Outline: user can rename an existing knowledge suite
    Given open knowledge suite <type>
    When rename by <trigger> for <type>
    Examples:
      | case              | type  | trigger |
      | rename in sidebar | page  | sidebar |
      | rename by title   | page  | title   |
      | rename in sidebar | slide | sidebar |
      | rename by title   | slide | title   |
      | rename in sidebar | base  | sidebar |
