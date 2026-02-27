from langchain_core.messages import AIMessage, HumanMessage

from app.core.agent import agent as agent_module
from app.core.agent.agent import Agent


def _build_agent() -> Agent:
    return Agent(
        agent_id="agent-history-limit-test",
        name="HistoryLimitAgent",
        model_config={},
    )


def test_get_chat_messages_limit_differs_by_subscription(monkeypatch):
    monkeypatch.setattr(
        agent_module.global_config.app.limits,
        "free_user_chat_messages_limit",
        2,
    )
    monkeypatch.setattr(
        agent_module.global_config.app.limits,
        "sub_user_chat_messages_limit",
        4,
    )
    agent = _build_agent()

    assert agent._get_chat_messages_limit(is_subscribed=False) == 2
    assert agent._get_chat_messages_limit(is_subscribed=True) == 4


def test_get_relevant_history_for_user_tier_uses_configured_window(monkeypatch):
    monkeypatch.setattr(
        agent_module.global_config.app.limits,
        "free_user_chat_messages_limit",
        2,
    )
    monkeypatch.setattr(
        agent_module.global_config.app.limits,
        "sub_user_chat_messages_limit",
        4,
    )
    history_messages = [
        HumanMessage(content="h1"),
        AIMessage(content="a1"),
        HumanMessage(content="h2"),
        AIMessage(content="a2"),
        HumanMessage(content="h3"),
        AIMessage(content="a3"),
    ]
    agent = _build_agent()

    free_user_history = agent._get_relevant_history_for_user_tier(
        history_messages=history_messages,
        is_subscribed=False,
    )
    sub_user_history = agent._get_relevant_history_for_user_tier(
        history_messages=history_messages,
        is_subscribed=True,
    )

    assert [message.content for message in free_user_history] == ["h3", "a3"]
    assert [message.content for message in sub_user_history] == ["h2", "a2", "h3", "a3"]
