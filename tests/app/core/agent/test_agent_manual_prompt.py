# CREATED_BY_AGENT
from app.core.agent import agent as agent_module
from app.core.agent.agent import Agent, INTELLIMATE_AGENT_ID, INTELLIMATE_AGENT_NAME


def _build_agent(*, agent_id: str, name: str, personality: str) -> Agent:
    return Agent(
        agent_id=agent_id,
        name=name,
        model_config={},
        personality=personality,
    )


def _get_contents(messages) -> list[str]:
    return [message.content for message in messages]


def test_intellimate_official_injects_manual_prompt(monkeypatch):
    monkeypatch.setattr(
        agent_module, "_load_intellimate_user_manual", lambda: "MANUAL_CONTENT"
    )
    agent = _build_agent(
        agent_id=INTELLIMATE_AGENT_ID,
        name=INTELLIMATE_AGENT_NAME,
        personality="Warm personality.",
    )
    contents = _get_contents(agent.build_system_messages("", None))

    assert any(
        "##IntelliMate User Manual\nMANUAL_CONTENT" in content
        for content in contents
    )


def test_intellimate_official_renders_manual_placeholder_in_personality(monkeypatch):
    monkeypatch.setattr(
        agent_module, "_load_intellimate_user_manual", lambda: "MANUAL_CONTENT"
    )
    agent = _build_agent(
        agent_id=INTELLIMATE_AGENT_ID,
        name=INTELLIMATE_AGENT_NAME,
        personality="Manual: {{ intellimate_user_manual }}",
    )
    contents = _get_contents(agent.build_system_messages("", None))

    assert any("Manual: MANUAL_CONTENT" in content for content in contents)
    assert not any(
        content.startswith("##IntelliMate User Manual") for content in contents
    )


def test_non_official_agent_does_not_inject_manual_prompt(monkeypatch):
    monkeypatch.setattr(
        agent_module, "_load_intellimate_user_manual", lambda: "MANUAL_CONTENT"
    )
    agent = _build_agent(
        agent_id="not-intellimate",
        name="OtherAgent",
        personality="Warm personality.",
    )
    contents = _get_contents(agent.build_system_messages("", None))

    assert not any(
        "##IntelliMate User Manual\nMANUAL_CONTENT" in content
        for content in contents
    )
