from types import SimpleNamespace

import pytest

from app.core.agent.agent import (
    OFFICIAL_ASSISTANT_SAVE_USER_MBTI_TOOL_NAME,
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
    tool_call = SimpleNamespace(id="tool-call-1", type="function", function=function)
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

    def fake_execute_official_assistant_tool_call(*, tool_name, raw_arguments, user_id):
        captured["tool_name"] = tool_name
        captured["raw_arguments"] = raw_arguments
        assert user_id == "user-1"
        return "Saved MBTI type: ENFP"

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
        return final_response

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

    response, messages = agent._resolve_official_assistant_tool_calls(
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


def test_get_user_profile_sync_includes_mbti_type_when_present(
    monkeypatch: pytest.MonkeyPatch,
):
    """When users.meta_data has mbti_type, the user info section includes 'MBTI Type: <type>'."""
    agent = _build_official_agent()
    user_id = "user-mbti-test"
    # Row: nickname, gender, age_group, description, system_language, meta_data
    fake_row = (None, None, None, None, None, {"mbti_type": "INTP"})
    fake_result = SimpleNamespace(fetchone=lambda: fake_row)
    fake_conn = SimpleNamespace(execute=lambda query, params: fake_result)

    class FakeConnectionManager:
        def __enter__(self):
            return fake_conn

        def __exit__(self, *args):
            return None

    fake_engine = SimpleNamespace(connect=lambda: FakeConnectionManager())

    monkeypatch.setattr(
        "app.core.agent.agent.cache_service.get_user_info",
        lambda uid: None,
    )
    monkeypatch.setattr(
        "app.core.agent.agent.cache_service.set_user_info",
        lambda uid, text, ttl=60: None,
    )
    monkeypatch.setattr(
        "app.core.agent.agent.get_sync_engine",
        lambda: fake_engine,
    )
    monkeypatch.setattr(
        "app.services.memory_service.get_user_memory_for_prompt_sync",
        lambda uid: "",
    )

    profile = agent._get_user_profile_sync(user_id)

    assert "##User Information" in profile
    assert "MBTI Type: INTP" in profile
