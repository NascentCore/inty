from types import SimpleNamespace

import pytest

from app.core.agent import agent as agent_module
from app.core.agent.agent import (
    INTELLIMATE_CHANGE_LOGS_SYSTEM_MESSAGE_PREFIX,
    INTELLIMATE_USER_MANUAL_SYSTEM_MESSAGE_PREFIX,
    OFFICIAL_ASSISTANT_READ_CHANGE_LOGS_TOOL_NAME,
    OFFICIAL_ASSISTANT_READ_USER_MANUAL_TOOL_NAME,
    OFFICIAL_ASSISTANT_SAVE_USER_MBTI_TOOL_NAME,
    OFFICIAL_ASSISTANT_TOOL_DEFINITIONS,
    Agent,
)
from app.core.agent.agent_prompt_configs import INTELLIMATE_AGENT_ID


def _build_official_agent() -> Agent:
    return Agent(
        agent_id=INTELLIMATE_AGENT_ID,
        name="Inty",
        model_config={"model": "test-model"},
    )


def _build_openai_response_with_tool_call(
    *,
    tool_name: str,
    tool_arguments: str,
    content: str = "",
):
    function = SimpleNamespace(name=tool_name, arguments=tool_arguments)
    tool_call = SimpleNamespace(
        id="tool-call-1", type="function", function=function
    )
    message = SimpleNamespace(content=content, tool_calls=[tool_call])
    choice = SimpleNamespace(message=message, finish_reason="tool_calls")
    return SimpleNamespace(choices=[choice], model="test-model", usage=None)


def _build_openai_response_without_tool_call(*, content: str):
    message = SimpleNamespace(content=content, tool_calls=None)
    choice = SimpleNamespace(message=message, finish_reason="stop")
    return SimpleNamespace(choices=[choice], model="test-model", usage=None)


def test_parse_mbti_tool_arguments_normalizes_to_uppercase():
    agent = _build_official_agent()
    parsed = agent._parse_mbti_type_from_tool_arguments('{"mbti_type":"infj"}')
    assert parsed == "INFJ"


def test_parse_mbti_tool_arguments_rejects_invalid_type():
    agent = _build_official_agent()
    with pytest.raises(ValueError):
        agent._parse_mbti_type_from_tool_arguments('{"mbti_type":"ABCD"}')


def test_official_tool_definitions_include_manual_and_change_logs_reader():
    tool_names = {
        tool_definition["function"]["name"]
        for tool_definition in OFFICIAL_ASSISTANT_TOOL_DEFINITIONS
    }
    assert OFFICIAL_ASSISTANT_READ_USER_MANUAL_TOOL_NAME in tool_names
    assert OFFICIAL_ASSISTANT_READ_CHANGE_LOGS_TOOL_NAME in tool_names
    assert OFFICIAL_ASSISTANT_SAVE_USER_MBTI_TOOL_NAME in tool_names


def test_resolve_official_tool_calls_executes_tool_and_returns_final_response(
    monkeypatch: pytest.MonkeyPatch,
):
    agent = _build_official_agent()
    initial_response = _build_openai_response_with_tool_call(
        tool_name=OFFICIAL_ASSISTANT_SAVE_USER_MBTI_TOOL_NAME,
        tool_arguments='{"mbti_type":"enfp"}',
        content="I will save your MBTI now.",
    )
    final_response = _build_openai_response_without_tool_call(
        content="Saved. Your MBTI type is ENFP.",
    )

    captured = {"tool_name": None, "raw_arguments": None, "retry_called": False}

    def fake_execute_official_assistant_tool_call(
        *, tool_name, raw_arguments, user_id
    ):
        captured["tool_name"] = tool_name
        captured["raw_arguments"] = raw_arguments
        assert user_id == "user-1"
        return "Saved MBTI type: ENFP", None

    def fake_call_openai_api_with_retry(**kwargs):
        captured["retry_called"] = True
        assert kwargs["tools"] is not None
        openai_messages = kwargs["openai_messages"]
        assert openai_messages[-2]["role"] == "assistant"
        assert openai_messages[-2]["tool_calls"][0]["function"]["name"] == (
            OFFICIAL_ASSISTANT_SAVE_USER_MBTI_TOOL_NAME
        )
        assert openai_messages[-1]["role"] == "tool"
        assert openai_messages[-1]["content"] == "Saved MBTI type: ENFP"
        return (final_response, None)

    monkeypatch.setattr(
        agent,
        "_execute_official_assistant_tool_call",
        fake_execute_official_assistant_tool_call,
    )
    monkeypatch.setattr(
        agent,
        "_call_openai_api_with_retry",
        fake_call_openai_api_with_retry,
    )

    response, messages, _ = agent._resolve_official_assistant_tool_calls(
        response=initial_response,
        openai_messages=[{"role": "user", "content": "Please test my MBTI."}],
        client=object(),
        model="test-model",
        temperature=0.7,
        max_tokens=256,
        top_p=0.9,
        extra_body={"user": "user-1"},
        user_id="user-1",
        chat_name="test-chat",
        labels={},
    )

    assert captured["retry_called"] is True
    assert captured["tool_name"] == OFFICIAL_ASSISTANT_SAVE_USER_MBTI_TOOL_NAME
    assert captured["raw_arguments"] == '{"mbti_type":"enfp"}'
    assert response is final_response
    assert messages[-1]["role"] == "tool"


def test_read_user_manual_tool_returns_system_message(
    monkeypatch: pytest.MonkeyPatch,
):
    agent = _build_official_agent()
    monkeypatch.setattr(
        agent_module, "_load_intellimate_user_manual", lambda: "MANUAL_ABC"
    )

    tool_result, injected_system_message = (
        agent._execute_official_assistant_tool_call(
            tool_name=OFFICIAL_ASSISTANT_READ_USER_MANUAL_TOOL_NAME,
            raw_arguments="{}",
            user_id="user-1",
        )
    )

    assert tool_result == "Loaded IntelliMate user manual into system context."
    assert (
        injected_system_message
        == INTELLIMATE_USER_MANUAL_SYSTEM_MESSAGE_PREFIX + "MANUAL_ABC"
    )


def test_read_change_logs_tool_returns_system_message(
    monkeypatch: pytest.MonkeyPatch,
):
    agent = _build_official_agent()
    monkeypatch.setattr(
        agent_module, "_load_intellimate_change_logs", lambda: "CHANGE_LOGS_ABC"
    )

    tool_result, injected_system_message = (
        agent._execute_official_assistant_tool_call(
            tool_name=OFFICIAL_ASSISTANT_READ_CHANGE_LOGS_TOOL_NAME,
            raw_arguments="{}",
            user_id="user-1",
        )
    )

    assert tool_result == "Loaded IntelliMate change logs into system context."
    assert (
        injected_system_message
        == INTELLIMATE_CHANGE_LOGS_SYSTEM_MESSAGE_PREFIX + "CHANGE_LOGS_ABC"
    )


def test_resolve_official_tool_calls_injects_manual_as_system_message(
    monkeypatch: pytest.MonkeyPatch,
):
    agent = _build_official_agent()
    initial_response = _build_openai_response_with_tool_call(
        tool_name=OFFICIAL_ASSISTANT_READ_USER_MANUAL_TOOL_NAME,
        tool_arguments="{}",
        content="Let me check the user manual first.",
    )
    final_response = _build_openai_response_without_tool_call(
        content="Here is how to use IntelliMate...",
    )
    monkeypatch.setattr(
        agent_module, "_load_intellimate_user_manual", lambda: "MANUAL_XYZ"
    )

    def fake_call_openai_api_with_retry(**kwargs):
        openai_messages = kwargs["openai_messages"]
        assert any(
            message["role"] == "system"
            and message["content"]
            == INTELLIMATE_USER_MANUAL_SYSTEM_MESSAGE_PREFIX + "MANUAL_XYZ"
            for message in openai_messages
        )
        return (final_response, None)

    monkeypatch.setattr(
        agent, "_call_openai_api_with_retry", fake_call_openai_api_with_retry
    )

    response, _, _ = agent._resolve_official_assistant_tool_calls(
        response=initial_response,
        openai_messages=[{"role": "system", "content": "BASE_SYSTEM"}],
        client=object(),
        model="test-model",
        temperature=0.7,
        max_tokens=256,
        top_p=0.9,
        extra_body={"user": "user-1"},
        user_id="user-1",
        chat_name="test-chat",
        labels={},
    )

    assert response is final_response


def test_resolve_official_tool_calls_injects_change_logs_as_system_message(
    monkeypatch: pytest.MonkeyPatch,
):
    agent = _build_official_agent()
    initial_response = _build_openai_response_with_tool_call(
        tool_name=OFFICIAL_ASSISTANT_READ_CHANGE_LOGS_TOOL_NAME,
        tool_arguments="{}",
        content="Let me check the change logs first.",
    )
    final_response = _build_openai_response_without_tool_call(
        content="Here are the latest updates...",
    )
    monkeypatch.setattr(
        agent_module, "_load_intellimate_change_logs", lambda: "CHANGE_LOGS_XYZ"
    )

    def fake_call_openai_api_with_retry(**kwargs):
        openai_messages = kwargs["openai_messages"]
        assert any(
            message["role"] == "system"
            and message["content"]
            == INTELLIMATE_CHANGE_LOGS_SYSTEM_MESSAGE_PREFIX + "CHANGE_LOGS_XYZ"
            for message in openai_messages
        )
        return (final_response, None)

    monkeypatch.setattr(
        agent, "_call_openai_api_with_retry", fake_call_openai_api_with_retry
    )

    response, _, _ = agent._resolve_official_assistant_tool_calls(
        response=initial_response,
        openai_messages=[{"role": "system", "content": "BASE_SYSTEM"}],
        client=object(),
        model="test-model",
        temperature=0.7,
        max_tokens=256,
        top_p=0.9,
        extra_body={"user": "user-1"},
        user_id="user-1",
        chat_name="test-chat",
        labels={},
    )

    assert response is final_response
