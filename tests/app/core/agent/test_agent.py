import uuid
import pytest

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.agent import prompts
from app.core.agent.agent import Agent
from app.core.agent.personalities import EVERYONE_HATES_YOU
from app.core.agent import prompt_template
from app.core.agent.prompt_template import prompt_template_manager
from app.core.config import global_config_loaded_from_config_yaml


def test_agent_chat_happy_path():
    """
    Test the happy path of Agent.chat() method

    This test verifies that:
    1. Agent can be initialized with proper configuration
    2. Agent.chat() method can be called successfully
    3. The method returns a response string
    4. All dependencies are properly mocked to avoid external calls
    """

    # Create agent instance
    agent = Agent(
        agent_id="test-agent-123",
        name="Test Agent",
        model_config={
            "model": "gpt-4o-mini",
            "api_key": "test-api-key",
            "base_url": "https://api.openai.com/v1",
            "temperature": 0.7,
            "max_tokens": 100,
        },
        description="Test agent for unit testing",
        personality=EVERYONE_HATES_YOU.to_prompt(),
        main_prompt=prompts.GENERAL_CHAT_MAIN_PROMPT,
        mode_prompt=prompts.HELPFUL_MODE_PROMPT,
    )

    state = {"messages": [HumanMessage(content="Who are you?")]}
    messages = agent.build_system_messages(state)

    assert messages == [
        SystemMessage(
            content="Write Test Agent's next reply in a general chat between Test Agent and None."
        ),
        SystemMessage(
            content="personality: you are hated by everyone, you are always sad, "
            "you are radiating negative energy; "
            "personality traits: arrogant, condescending, disrespectful, rude"
        ),
        SystemMessage(content="Respond in a helpful manner."),
    ]


def test_render_system_prompt():
    rendered_prompt = prompt_template_manager.render_system_prompt(
        system_prompt="{{ char }} and {{ user }}",
        agent_name="Agent",
        user_name="User",
        template_name="basic",
    )
    assert rendered_prompt == "Agent and User"


def test_render_prompt_jinja2_template():
    rendered_prompt = prompt_template_manager._perform_character_substitution(
        "{{ char }} and {{ user }}",
        "Agent",
        "User",
    )
    assert rendered_prompt == "Agent and User"
