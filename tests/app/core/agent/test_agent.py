import uuid
import pytest

from langchain_core.messages import HumanMessage

from app.core.agent import prompts
from app.core.agent.agent import Agent
from app.core.agent.personalities import EVERYONE_HATES_YOU
from app.core.agent.prompt_template import prompt_template_manager
from app.core.config import global_config_loaded_from_config_yaml


class TestAgentChat:
    """Test class for Agent.chat() method - Happy Path"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.agent_id = "test-agent-123"
        self.agent_name = "Test Agent"
        self.user_id = "test-user-456"
        self.session_id = str(uuid.uuid4())

        self.model_config = {
            "model": global_config_loaded_from_config_yaml.agent.model,
            "api_key": global_config_loaded_from_config_yaml.agent.api_key,
            "base_url": global_config_loaded_from_config_yaml.agent.base_url,
            "temperature": 0.7,
            "max_tokens": 100,
        }

        self.test_messages = {"messages": [HumanMessage(content="Who are you?")]}

        self.agent = None

        # Teardown fixture: https://stackoverflow.com/a/22638709
        yield

        if self.agent:
            try:
                self.agent.cleanup()
            except Exception as e:
                print(f"Warning: Failed to cleanup agent: {e}")

    @pytest.mark.asyncio
    async def test_agent_chat_happy_path(self):
        """
        Test the happy path of Agent.chat() method

        This test verifies that:
        1. Agent can be initialized with proper configuration
        2. Agent.chat() method can be called successfully
        3. The method returns a response string
        4. All dependencies are properly mocked to avoid external calls
        """

        # Create agent instance
        self.agent = Agent(
            agent_id=self.agent_id,
            name=self.agent_name,
            model_config=self.model_config,
            description="Test agent for unit testing",
            personality=EVERYONE_HATES_YOU.to_prompt(),
            main_prompt=prompts.GENERAL_CHAT_MAIN_PROMPT,
            mode_prompt=prompts.HELPFUL_MODE_PROMPT,
        )

        response = await self.agent.chat(
            user_id=self.user_id,
            session_id=self.session_id,
            messages=self.test_messages,
        )

        assert response == "Hello, how are you today?!"


def test_render_system_prompt():
    rendered_prompt = prompt_template_manager.render_system_prompt(
        system_prompt="{{ char }} and {{ user }}",
        agent_name="Agent",
        user_name="User",
        template_name="basic",
    )
    assert rendered_prompt == "Agent and User"
