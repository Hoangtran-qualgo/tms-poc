@customer_portal @auto
Feature: Current User

  Scenario: Verify retrieve the authenticated user's current profile
    Given I am authenticated as admin
    When I get my current user profile
    Then my current user profile response should be successful
