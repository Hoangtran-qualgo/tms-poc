@customer_portal @auto
Feature: Current User

  Scenario: Verify retrieve the authenticated user's onboarding state
    Given I am authenticated as admin
    When I get my onboarding state
    Then my onboarding state response should be successful
