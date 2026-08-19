@customer_portal @auto
Feature: KChat Tenant Members

  Scenario: Verify retrieve members of the Pro workspace KChat tenant
    Given I am authenticated as admin
    When I get the KChat tenant id of the pro workspace
    And I list members of the captured KChat tenant
    Then the KChat tenant members response should be successful
