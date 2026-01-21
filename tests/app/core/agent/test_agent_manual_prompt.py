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

    assert contents[-1] == "##IntelliMate User Manual\nMANUAL_CONTENT"


def test_non_intellimate_official_does_not_inject_manual_prompt(monkeypatch):
    monkeypatch.setattr(
        agent_module, "_load_intellimate_user_manual", lambda: "MANUAL_CONTENT"
    )
    agent = _build_agent(
        agent_id="not_intellimate",
        name="Not IntelliMate",
        personality="Warm personality.",
    )
    contents = _get_contents(agent.build_system_messages("", None))

    assert not any("##IntelliMate User Manual\n" in content for content in contents)
