from langchain_core.messages import AIMessage, HumanMessage

from app.core.agent import agent as agent_module
from app.core.agent.agent import Agent


def _build_agent() -> Agent:
    return Agent(
        agent_id="agent-compaction-test",
        name="CompactionAgent",
        model_config={},
    )


def test_maybe_compact_history_for_user_tier_triggers_on_overflow(monkeypatch):
    monkeypatch.setattr(
        agent_module.global_config.app.limits,
        "free_user_chat_messages_limit",
        2,
    )
    history_messages = [
        HumanMessage(content="h1"),
        AIMessage(content="a1"),
        HumanMessage(content="h2"),
        AIMessage(content="a2"),
    ]
    captured = {}

    def fake_compact(**kwargs):
        captured.update(kwargs)
        return True

    monkeypatch.setattr(
        agent_module,
        "maybe_compact_and_save_overflow_history",
        fake_compact,
    )

    agent = _build_agent()
    agent._maybe_compact_history_for_user_tier(
        user_id="user-1",
        session_id="session-1",
        history_messages=history_messages,
        is_subscribed=False,
    )

    assert captured["user_id"] == "user-1"
    assert captured["agent_id"] == "agent-compaction-test"
    assert captured["session_id"] == "session-1"
    assert captured["max_messages_limit"] == 2
    assert len(captured["history_messages"]) == 4


def test_maybe_compact_history_for_user_tier_skips_when_within_limit(monkeypatch):
    monkeypatch.setattr(
        agent_module.global_config.app.limits,
        "free_user_chat_messages_limit",
        10,
    )
    history_messages = [
        HumanMessage(content="h1"),
        AIMessage(content="a1"),
    ]

    captured = {}

    def fake_compact(**kwargs):
        captured.update(kwargs)
        return False

    monkeypatch.setattr(
        agent_module,
        "maybe_compact_and_save_overflow_history",
        fake_compact,
    )

    agent = _build_agent()
    agent._maybe_compact_history_for_user_tier(
        user_id="user-1",
        session_id="session-1",
        history_messages=history_messages,
        is_subscribed=False,
    )
    assert captured["max_messages_limit"] == 10
    assert len(captured["history_messages"]) == 2
