# 验证 chat completions 时传给 OpenAI client 的完整 messages 结构
from datetime import datetime, timezone
from unittest.mock import patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.core.agent import agent as agent_module
from app.core.agent.agent import (
    Agent,
    USER_TIME_CONTEXT_INTERVAL_MESSAGES,
)
from app.external_services.fakes.openai import FakeOpenAI
from app.utils.openai_client import langchain_message_to_openai_message


def _build_agent() -> Agent:
    return Agent(
        agent_id="agent-chat-messages-test",
        name="ChatMessagesAgent",
        model_config={"model": "test-model"},
        personality="Friendly.",
    )


def _capture_openai_messages(agent_instance: Agent):
    """返回一个 (captured_list, 原始 _call_openai_api_with_retry) 的包装，调用后 captured_list 即本次传入的 openai_messages。"""
    captured: list = []
    original = agent_instance._call_openai_api_with_retry

    def wrapper(*args, **kwargs):
        openai_messages = kwargs.get("openai_messages") or (args[2] if len(args) > 2 else [])
        captured[:] = [openai_messages]
        return original(*args, **kwargs)

    return captured, wrapper


def test_chat_completion_messages_structure_and_user_time_context(monkeypatch):
    """
    调用 _generate_message_without_user_save_sync 时，验证传给 OpenAI client 的 messages：
    - 先是一组 system 消息（角色设定等），再是对话消息（按频率注入的 User Time Context system、user/assistant）
    - 当开启 user time context 且传入 user_time_context 时，对话部分按“每 N 条消息或每 X 分钟”插入 ##User Time Context
    """
    monkeypatch.setattr(
        agent_module.global_config.app.features,
        "experimental_enable_chat_with_user_time_context",
        True,
    )
    agent = _build_agent()
    captured, wrapper = _capture_openai_messages(agent)
    monkeypatch.setattr(agent, "_call_openai_api_with_retry", wrapper)

    with (
        patch.object(
            agent_module.chat_history_service,
            "get_history_messages",
            return_value=[
                HumanMessage(content="human message 1"),
                AIMessage(content="ai message 1"),
                HumanMessage(content="human message 2"),
                AIMessage(content="ai message 2"),
                HumanMessage(content="human message 3"),
                AIMessage(content="ai message 3"),
            ],
        ),
        patch(
            "app.core.agent.agent.get_base_openai_client",
            return_value=FakeOpenAI(),
        ),
    ):
        agent._generate_message_without_user_save_sync(
            user_id="user-1",
            session_id="session-1",
            messages=[HumanMessage(content="Hello")],
            user_profile="Name: TestUser",
            chat_settings=None,
            user_time_context={
                "local_time": "2026-03-02 6:41:23 pm",
                "timezone": "America/Los_Angeles",
                "utc_offset_minutes": -480,
            },
            model_override="test-model",
            is_subscribed=True,
        )

    # captured 是 [openai_messages]，即单次调用的消息列表；构造期望的 message 列表并逐条比对
    assert len(captured) == 1
    openai_messages = captured[0]

    user_time_context = {
        "local_time": "2026-03-02 6:41:23 pm",
        "timezone": "America/Los_Angeles",
        "utc_offset_minutes": -480,
    }
    user_name = "TestUser"
    agent_name = "ChatMessagesAgent"

    # 与 agent 相同的 system 块
    system_messages = agent.build_system_messages(
        "Name: TestUser", None, user_time_context
    )
    expected_system = [
        langchain_message_to_openai_message(m, user_name, agent_name)
        for m in system_messages
    ]

    # 对话部分：仅按频率注入 User Time Context（每 N 条消息或每 X 分钟），不插入 date prompt
    history_messages = [
        HumanMessage(content="human message 1"),
        AIMessage(content="ai message 1"),
        HumanMessage(content="human message 2"),
        AIMessage(content="ai message 2"),
        HumanMessage(content="human message 3"),
        AIMessage(content="ai message 3"),
    ]
    current_messages = [HumanMessage(content="Hello")]
    now_utc = datetime.now(timezone.utc)
    conversation_messages = agent._inject_user_time_context_periodically(
        history_messages + current_messages, user_time_context, now_utc
    )
    expected_conversation = [
        langchain_message_to_openai_message(m, user_name, agent_name)
        for m in conversation_messages
    ]
    expected = expected_system + expected_conversation

    assert openai_messages == expected


def test_chat_completion_messages_with_history_includes_date_and_time_context(monkeypatch):
    """
    有历史消息时，传给 client 的 messages 中应包含按频率注入的 User Time Context system（在对话中），以及历史 human/ai 与当前 user。
    """
    monkeypatch.setattr(
        agent_module.global_config.app.features,
        "experimental_enable_chat_with_user_time_context",
        True,
    )
    agent = _build_agent()
    captured, wrapper = _capture_openai_messages(agent)
    monkeypatch.setattr(agent, "_call_openai_api_with_retry", wrapper)

    history = [
        HumanMessage(
            content="history user",
            additional_kwargs={"created_at": "2026-03-02T10:00:00+00:00"},
        ),
        AIMessage(
            content="history assistant",
            additional_kwargs={"created_at": "2026-03-02T10:01:00+00:00"},
        ),
    ]

    with (
        patch.object(
            agent_module.chat_history_service,
            "get_history_messages",
            return_value=history,
        ),
        patch(
            "app.core.agent.agent.get_base_openai_client",
            return_value=FakeOpenAI(),
        ),
    ):
        agent._generate_message_without_user_save_sync(
            user_id="user-1",
            session_id="session-1",
            messages=[HumanMessage(content="Current message")],
            user_profile="Name: TestUser",
            chat_settings=None,
            user_time_context={
                "local_time": "2026-03-02 6:41:23 pm",
                "timezone": "America/Los_Angeles",
                "utc_offset_minutes": -480,
            },
            model_override="test-model",
            is_subscribed=True,
        )

    # 与第一则测试相同：构造期望的 message 列表并逐条比对
    assert len(captured) == 1
    openai_messages = captured[0]

    user_time_context = {
        "local_time": "2026-03-02 6:41:23 pm",
        "timezone": "America/Los_Angeles",
        "utc_offset_minutes": -480,
    }
    user_name = "TestUser"
    agent_name = "ChatMessagesAgent"

    system_messages = agent.build_system_messages(
        "Name: TestUser", None, user_time_context
    )
    expected_system = [
        langchain_message_to_openai_message(m, user_name, agent_name)
        for m in system_messages
    ]

    # 对话部分：仅按频率注入 User Time Context，不插入 date prompt
    history_messages = [
        HumanMessage(
            content="history user",
            additional_kwargs={"created_at": "2026-03-02T10:00:00+00:00"},
        ),
        AIMessage(
            content="history assistant",
            additional_kwargs={"created_at": "2026-03-02T10:01:00+00:00"},
        ),
    ]
    current_messages = [HumanMessage(content="Current message")]
    now_utc = datetime.now(timezone.utc)
    conversation_messages = agent._inject_user_time_context_periodically(
        history_messages + current_messages, user_time_context, now_utc
    )
    expected_conversation = [
        langchain_message_to_openai_message(m, user_name, agent_name)
        for m in conversation_messages
    ]
    expected = expected_system + expected_conversation

    assert openai_messages == expected


def test_chat_completion_messages_inject_three_user_time_contexts(monkeypatch):
    """
    当历史 + 当前消息数达到 22 条（21 history + 1 current）时，按“每 10 条消息”应插入 3 次
    User Time Context system message：第 1 条前、第 11 条前、第 21 条前。
    """
    monkeypatch.setattr(
        agent_module.global_config.app.features,
        "experimental_enable_chat_with_user_time_context",
        True,
    )
    agent = _build_agent()
    captured, wrapper = _capture_openai_messages(agent)
    monkeypatch.setattr(agent, "_call_openai_api_with_retry", wrapper)

    # 21 条历史（索引 0..20），使 _inject_user_time_context_periodically 在 0、10、20 处各注入一次
    history = []
    for i in range(USER_TIME_CONTEXT_INTERVAL_MESSAGES * 2 + 1):
        if i % 2 == 0:
            history.append(HumanMessage(content=f"user msg {i + 1}"))
        else:
            history.append(AIMessage(content=f"ai msg {i + 1}"))

    with (
        patch.object(
            agent_module.chat_history_service,
            "get_history_messages",
            return_value=history,
        ),
        patch(
            "app.core.agent.agent.get_base_openai_client",
            return_value=FakeOpenAI(),
        ),
    ):
        agent._generate_message_without_user_save_sync(
            user_id="user-1",
            session_id="session-1",
            messages=[HumanMessage(content="Current message")],
            user_profile="Name: TestUser",
            chat_settings=None,
            user_time_context={
                "local_time": "2026-03-02 6:41:23 pm",
                "timezone": "America/Los_Angeles",
                "utc_offset_minutes": -480,
            },
            model_override="test-model",
            is_subscribed=True,
        )

    assert len(captured) == 1
    openai_messages = captured[0]

    user_time_context = {
        "local_time": "2026-03-02 6:41:23 pm",
        "timezone": "America/Los_Angeles",
        "utc_offset_minutes": -480,
    }
    user_name = "TestUser"
    agent_name = "ChatMessagesAgent"

    system_messages = agent.build_system_messages(
        "Name: TestUser", None, user_time_context
    )
    expected_system = [
        langchain_message_to_openai_message(m, user_name, agent_name)
        for m in system_messages
    ]
    history_messages = list(history)
    current_messages = [HumanMessage(content="Current message")]
    now_utc = datetime.now(timezone.utc)
    conversation_messages = agent._inject_user_time_context_periodically(
        history_messages + current_messages, user_time_context, now_utc
    )
    expected_conversation = [
        langchain_message_to_openai_message(m, user_name, agent_name)
        for m in conversation_messages
    ]
    expected = expected_system + expected_conversation

    assert openai_messages == expected

    # 明确断言：对话部分（去掉开头 system 块）中有 3 条 User Time Context system 消息
    num_system = len(expected_system)
    conversation_part = openai_messages[num_system:]
    user_time_context_system = [
        m
        for m in conversation_part
        if m.get("role") == "system"
        and "##User Time Context" in (m.get("content") or "")
    ]
    assert len(user_time_context_system) == 3, (
        f"expected 3 User Time Context system messages in conversation, got {len(user_time_context_system)}"
    )
