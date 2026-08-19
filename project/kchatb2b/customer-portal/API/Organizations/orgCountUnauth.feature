@customer_portal @auto
Feature: Organizations

  Scenario: Verify retrieve organizations count without authorization
    When I get organizations count without authorization
    Then the organizations count response should be unauthorized
