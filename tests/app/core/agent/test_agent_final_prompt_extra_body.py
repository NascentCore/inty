# 测试 Agent._chat_extra_body、get_agent_model_config、build_agent_from_data（review 增强补充）
from types import SimpleNamespace

import pytest

from app.core.agent import agent as agent_module
from app.core.agent.agent import Agent, build_agent_from_data, get_agent_model_config


def _minimal_agent(**kwargs) -> Agent:
    """构建最小 Agent，仅传必要参数与待测字段。"""
    return Agent(
        agent_id=kwargs.get("agent_id", "test-agent"),
        name=kwargs.get("name", "Test"),
        model_config=kwargs.get("model_config", {}),
        **{k: v for k, v in kwargs.items() if k not in ("agent_id", "name", "model_config")},
    )


def test_get_agent_model_config_empty_when_no_config():
    """get_agent_model_config 无默认回退：无 settings 或无 llm_config 时返回空字典。"""
    assert get_agent_model_config({}) == {}
    assert get_agent_model_config({"settings": {}}) == {}
    assert get_agent_model_config({"settings": {"llm_config": None}}) == {}
    assert get_agent_model_config({"settings": {"llm_config": {}}}) == {}


def test_get_agent_model_config_legacy_model_config():
    """向后兼容：仅有旧字段 model_config 时取其值（dict），非 dict 则回退为空。"""
    assert get_agent_model_config({
        "settings": {"model_config": {"model": "gpt-4"}},
    }) == {"model": "gpt-4"}
    assert get_agent_model_config({"settings": {"model_config": None}}) == {}
    assert get_agent_model_config({"settings": {"model_config": "invalid"}}) == {}


def test_build_agent_from_data_uses_config():
    """build_agent_from_data 使用 get_agent_model_config 且正确传递各字段。"""
    agent_data = {
        "name": "TestChar",
        "settings": {"llm_config": {"model": "test-model", "temperature": 0.7}},
        "main_prompt": "Main",
        "personality": "Personality",
    }
    agent = build_agent_from_data("agent-1", agent_data)
    assert agent.agent_id == "agent-1"
    assert agent.name == "TestChar"
    assert agent.model_config == {"model": "test-model", "temperature": 0.7}
    assert agent.main_prompt == "Main"
    assert agent.personality == "Personality"


def test_chat_extra_body_gemini_model():
    """Non-DeepSeek models get generation_config.thinking_budget."""
    agent = _minimal_agent()
    got = agent._chat_extra_body("user_123", "google/gemini-2.5-flash")
    assert got == {
        "generation_config": {"thinking_budget": 0},
        "user": "user_123",
    }


def test_chat_extra_body_deepseek_model():
    """DeepSeek models on OpenRouter get reasoning config instead of thinking_budget."""
    agent = _minimal_agent()
    got = agent._chat_extra_body("user_123", "deepseek/deepseek-v3.2")
    assert got == {
        "reasoning": {"effort": "low", "exclude": True},
        "user": "user_123",
    }
    assert "generation_config" not in got


def test_chat_extra_body_different_user_id():
    """_chat_extra_body 的 user 字段与传入的 user_id 一致。"""
    agent = _minimal_agent()
    assert agent._chat_extra_body("another_user", "google/gemini-2.5-flash")["user"] == "another_user"


def test_call_openai_api_with_retry_retries_when_choices_are_empty(
    monkeypatch: pytest.MonkeyPatch,
):
    """上游返回空 choices 时应按可重试错误处理，直到拿到有效响应。"""

    class DummyCompletions:
        def __init__(self):
            self._responses = [
                SimpleNamespace(choices=[], model="test-model", usage=None),
                SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(content="ok", tool_calls=None),
                            finish_reason="stop",
                        )
                    ],
                    model="test-model",
                    usage=None,
                ),
            ]
            self.call_count = 0

        def create(self, **kwargs):
            response = self._responses[self.call_count]
            self.call_count += 1
            return response

    completions = DummyCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    agent = _minimal_agent()
    monkeypatch.setattr(agent_module, "_should_trace", lambda _email: False)

    response, trace_id = agent._call_openai_api_with_retry(
        client=client,
        model="google/gemini-2.5-flash",
        openai_messages=[{"role": "user", "content": "hello"}],
        temperature=0.7,
        max_tokens=128,
        top_p=1.0,
        extra_body={"user": "user-123"},
        user_id="user-123",
        max_retries=3,
        initial_delay=0.0,
        user_email="user@example.com",
    )

    assert completions.call_count == 2
    assert response.choices[0].message.content == "ok"
    assert trace_id is None


def test_call_openai_api_with_retry_raises_after_empty_choices_exhaust_retries(
    monkeypatch: pytest.MonkeyPatch,
):
    """连续空 choices 超过重试上限后应抛出原始错误。"""

    class DummyCompletions:
        def __init__(self):
            self.call_count = 0

        def create(self, **kwargs):
            self.call_count += 1
            return SimpleNamespace(choices=[], model="test-model", usage=None)

    completions = DummyCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    agent = _minimal_agent()
    monkeypatch.setattr(agent_module, "_should_trace", lambda _email: False)

    with pytest.raises(ValueError, match="LLM returned no choices"):
        agent._call_openai_api_with_retry(
            client=client,
            model="google/gemini-2.5-flash",
            openai_messages=[{"role": "user", "content": "hello"}],
            temperature=0.7,
            max_tokens=128,
            top_p=1.0,
            extra_body={"user": "user-123"},
            user_id="user-123",
            max_retries=2,
            initial_delay=0.0,
            user_email="user@example.com",
        )

    assert completions.call_count == 2
