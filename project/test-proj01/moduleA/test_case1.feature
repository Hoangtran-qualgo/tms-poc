# enum.components: login_account
# enum.sprint: init
@demo @test @reg @regress
Feature: test case 1

  Scenario:
    Given I login
    When I navigate to Home page
    Then I can see user info
