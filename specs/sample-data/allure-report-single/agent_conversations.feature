Feature: Agent Conversations
	@get_agent_conversation
  Scenario: Verify retrieve agent conversations list
    Given I am authenticated as fe-admin
    When I list agent conversations
    Then the agent conversations list response should be successful
	@get_agent_conversation_unauthorize
  Scenario: Verify retrieve agent conversations list without authorization
    When I list agent conversations without authorization
    Then the agent conversations list response should be unauthorized
	@get__agent_conversation_count
  Scenario Outline: Verify retrieve agent conversations count
    Given I am authenticated as fe-admin
    When I note the current agent conversations count
    And I create <no-conver> new test agent conversations
    And I count agent conversations
    Then the agent conversations count should have increased by <no-conver>
    When I delete the <no-conver> created test agent conversations
    Then the created test agent conversations should be deleted successfully

    Examples:
      | no-conver |
      | 1         |
      | 3         |
	@get_agent_conversation_count_unauthorize
  Scenario: Verify retrieve agent conversations count without authorization
    When I count agent conversations without authorization
    Then the agent conversations count response should be unauthorized
	@get_agent_conversation @post_agent_conversation @patch_agent_conversation @delete_agent_conversation
  Scenario: Verify CRUD agent conversation
    Given I am authenticated as fe-admin
    When I create a new agent conversation titled "Automation Conversation"
    Then the "Automation Conversation" agent conversation response should be created successfully
    When I get info of the "Automation Conversation" agent conversation
    Then the agent conversation response should be retrieved successfully
    When I update the "Automation Conversation" agent conversation title to "Automation Conversation Updated"
    Then the agent conversation response should be updated successfully
    When I delete the "Automation Conversation" agent conversation
    Then the agent conversation response should be deleted successfully
	@post_agent_conversation_empty_title
  Scenario: Verify create an agent conversation with empty title
    Given I am authenticated as fe-admin
    When I create a new agent conversation with empty title
    Then the agent conversation create response should be a bad request
	@get_agent_conversation_non_existent
  Scenario: Verify retrieve a non-existent agent conversation
    Given I am authenticated as fe-admin
    When I get a non-existent agent conversation
    Then the agent conversation response should be not found
	@delete_agent_conversation_non_existent
  Scenario: Verify delete a non-existent agent conversation
    Given I am authenticated as fe-admin
    When I delete a non-existent agent conversation
    Then the agent conversation response should be not found
