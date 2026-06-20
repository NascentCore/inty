from langchain_core.messages import AIMessage, HumanMessage

from app.core.agent import agent as agent_module
from app.core.agent.agent import Agent
from app.core.agent.agent_prompt_configs import INTELLIMATE_AGENT_ID


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
    assert [message.content for message in sub_user_history] == [
        "h2",
        "a2",
        "h3",
        "a3",
    ]


def test_official_assistant_uses_single_chat_messages_limit(monkeypatch):
    """官方助手不区分订阅，始终使用 agent.official_assistant_chat_messages_limit。"""
    monkeypatch.setattr(
        agent_module.global_config.agent,
        "official_assistant_chat_messages_limit",
        7,
    )
    agent = Agent(
        agent_id=INTELLIMATE_AGENT_ID,
        name="OfficialAssistant",
        model_config={},
    )
    assert agent._get_chat_messages_limit(is_subscribed=False) == 7
    assert agent._get_chat_messages_limit(is_subscribed=True) == 7


def test_official_assistant_get_relevant_history_uses_single_limit(monkeypatch):
    """官方助手 _get_relevant_history_for_user_tier 按单限制截断，与 is_subscribed 无关。"""
    monkeypatch.setattr(
        agent_module.global_config.agent,
        "official_assistant_chat_messages_limit",
        2,
    )
    history_messages = [
        HumanMessage(content="h1"),
        AIMessage(content="a1"),
        HumanMessage(content="h2"),
        AIMessage(content="a2"),
        HumanMessage(content="h3"),
        AIMessage(content="a3"),
    ]
    agent = Agent(
        agent_id=INTELLIMATE_AGENT_ID,
        name="OfficialAssistant",
        model_config={},
    )
    free_history = agent._get_relevant_history_for_user_tier(
        history_messages=history_messages,
        is_subscribed=False,
    )
    sub_history = agent._get_relevant_history_for_user_tier(
        history_messages=history_messages,
        is_subscribed=True,
    )
    assert [m.content for m in free_history] == ["h3", "a3"]
    assert [m.content for m in sub_history] == ["h3", "a3"]
