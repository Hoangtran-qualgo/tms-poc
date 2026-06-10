# enum.components: login
# enum.sprint: init
Feature: test case 1

  Scenario:
    Given I login
    When I navigate to Home page
    Then I can see user info
