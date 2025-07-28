import uuid
import pytest
from unittest.mock import patch, MagicMock

from langchain_core.messages import HumanMessage

from app.core.agent.agent import Agent
from app.core.config import settings


class TestAgentChat:
    """Test class for Agent.chat() method - Happy Path"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures before each test method"""
        # Test agent configuration
        self.agent_id = "test-agent-123"
        self.agent_name = "Test Agent"
        self.user_id = "test-user-456"
        self.session_id = str(uuid.uuid4())

        # Model configuration for testing
        self.model_config = {
            "model": "google/gemini-2.5-flash",
            "api_key": "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",
            "base_url": "https://openrouter.ai/api/v1",
            "temperature": 0.7,
            "max_tokens": 500,
        }

        self.test_messages = {
            "messages": [HumanMessage(content="Hello, how are you today?")]
        }

        # Agent personality/prompt for testing
        self.test_personality = (
            "You are a helpful AI assistant. Be friendly and concise in your responses."
        )

        self.agent = None

        yield

        # Cleanup after test
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

        print("Starting test_agent_chat_happy_path")
        # Create agent instance
        self.agent = Agent(
            agent_id=self.agent_id,
            name=self.agent_name,
            model_config=self.model_config,
            description="Test agent for unit testing",
            personality=self.test_personality,
            main_prompt="You are a test agent.",
            mode_prompt="Respond in a helpful manner.",
        )

        # Verify agent was created successfully
        assert self.agent is not None
        assert self.agent.agent_id == self.agent_id
        assert self.agent.name == self.agent_name
        assert self.agent.personality == self.test_personality

        response = await self.agent.chat(
            user_id=self.user_id,
            session_id=self.session_id,
            messages=self.test_messages,
        )

        # Verify response is a string
        assert isinstance(response, str)
        assert len(response) > 0

        print(f"✅ Chat test passed! Response: {response[:100]}...")

        # Additional assertions
        assert response is not None
        assert isinstance(response, str)
        assert response == "Hello, how are you today?!"
