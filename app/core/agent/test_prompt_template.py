import pytest

from app.core.agent.prompt_template import PromptTemplateManager, TemplateConfig


def test_render_system_prompt():
    """Test the render_system_prompt method with default template and character substitution"""

    # Create a new template manager instance
    manager = PromptTemplateManager()

    # Test data
    system_prompt = "Your name is {{ char }} and you are talking to {{ user }}"
    agent_name = "Alice"
    user_name = "Bob"

    # Call the method under test
    result = manager.render_system_prompt(
        system_prompt=system_prompt,
        agent_name=agent_name,
        user_name=user_name,
        template_name="basic",
    )

    assert result == "Your name is Alice and you are talking to Bob"
