from langchain_core.messages import HumanMessage
from app.core.agent.agent import Agent
import uuid
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

from app.core.agent import prompt_template, prompts
from app.core.agent.agent import Agent
from app.core.agent.personalities import EVERYONE_HATES_YOU, EVERYONE_LIKES_YOU
from app.core.config import global_config_loaded_from_config_yaml


def test_agent__create_dynamic_prompt_runnable():
    agent = Agent(
        agent_id="test",
        name="test",
        model_config={},
    )
    runnable = agent._create_dynamic_prompt_runnable()
    runnable.invoke({"user_profile": "test", "messages": [HumanMessage(content="test")]})


def test_render_prompt_jinja2_template():
    rendered_prompt = prompt_template.render_prompt_jinja2_template(
        "{{ char }} and {{ user }}",
        "Agent",
        "User",
    )
    assert rendered_prompt == "Agent and User"
