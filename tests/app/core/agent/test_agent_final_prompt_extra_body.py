# 测试 Agent._chat_extra_body、get_agent_model_config、build_agent_from_data（review 增强补充）
from types import SimpleNamespace

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


def test_build_chat_model_candidates_prioritizes_agent_then_fallbacks():
    agent_model = "google/gemini-2.5-flash"
    override_model = "google/gemini-2.5-flash-lite"
    agent = _minimal_agent(model_config={"model": agent_model})

    candidates = agent._build_chat_model_candidates(
        model_override=override_model,
        is_subscribed=False,
    )

    assert candidates[0] == agent_module.resolve_chat_model_to_id(agent_model)
    assert (
        agent_module.resolve_chat_model_to_id(override_model) in candidates
    )
    assert (
        agent_module.resolve_chat_model_to_id(
            agent_module.global_config.agent.sub_user_chat_model
        )
        in candidates
    )
    assert len(candidates) == len(set(candidates))


def test_call_chat_completion_with_model_fallback_retries_next_candidate_on_known_error():
    agent = _minimal_agent()
    calls = []
    success_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
    )

    def fake_call_openai_api_with_retry(**kwargs):
        calls.append(kwargs["model"])
        if kwargs["model"] == "model-a":
            raise ValueError("The provided model identifier is invalid.")
        return success_response, "trace-b"

    agent._call_openai_api_with_retry = fake_call_openai_api_with_retry

    response, trace_id, used_model = agent._call_chat_completion_with_model_fallback(
        client=None,
        model_candidates=["model-a", "model-b"],
        openai_messages=[{"role": "user", "content": "hi"}],
        temperature=0.7,
        max_tokens=1000,
        top_p=1.0,
        user_id="user-1",
        chat_name="chat-name",
        labels={},
    )

    assert calls == ["model-a", "model-b"]
    assert response is success_response
    assert trace_id == "trace-b"
    assert used_model == "model-b"


def test_call_chat_completion_with_model_fallback_retries_when_choices_empty():
    agent = _minimal_agent()
    calls = []
    empty_response = SimpleNamespace(choices=[])
    success_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="fallback-ok"))]
    )

    def fake_call_openai_api_with_retry(**kwargs):
        calls.append(kwargs["model"])
        if kwargs["model"] == "model-a":
            return empty_response, "trace-a"
        return success_response, "trace-b"

    agent._call_openai_api_with_retry = fake_call_openai_api_with_retry

    response, trace_id, used_model = agent._call_chat_completion_with_model_fallback(
        client=None,
        model_candidates=["model-a", "model-b"],
        openai_messages=[{"role": "user", "content": "hi"}],
        temperature=0.7,
        max_tokens=1000,
        top_p=1.0,
        user_id="user-1",
        chat_name="chat-name",
        labels={},
    )

    assert calls == ["model-a", "model-b"]
    assert response is success_response
    assert trace_id == "trace-b"
    assert used_model == "model-b"
