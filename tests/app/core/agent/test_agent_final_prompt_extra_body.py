# 测试 Agent._chat_extra_body、get_agent_model_config、build_agent_from_data（review 增强补充）
from app.core.agent.agent import (
    Agent,
    build_agent_from_data,
    get_agent_model_config,
)


def _minimal_agent(**kwargs) -> Agent:
    """构建最小 Agent，仅传必要参数与待测字段。"""
    return Agent(
        agent_id=kwargs.get("agent_id", "test-agent"),
        name=kwargs.get("name", "Test"),
        model_config=kwargs.get("model_config", {}),
        **{
            k: v
            for k, v in kwargs.items()
            if k not in ("agent_id", "name", "model_config")
        },
    )


def test_get_agent_model_config_empty_when_no_config():
    """get_agent_model_config 无默认回退：无 settings 或无 llm_config 时返回空字典。"""
    assert get_agent_model_config({}) == {}
    assert get_agent_model_config({"settings": {}}) == {}
    assert get_agent_model_config({"settings": {"llm_config": None}}) == {}
    assert get_agent_model_config({"settings": {"llm_config": {}}}) == {}


def test_get_agent_model_config_legacy_model_config():
    """向后兼容：仅有旧字段 model_config 时取其值（dict），非 dict 则回退为空。"""
    assert get_agent_model_config(
        {
            "settings": {"model_config": {"model": "gpt-4"}},
        }
    ) == {"model": "gpt-4"}
    assert get_agent_model_config({"settings": {"model_config": None}}) == {}
    assert (
        get_agent_model_config({"settings": {"model_config": "invalid"}}) == {}
    )


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
    assert (
        agent._chat_extra_body("another_user", "google/gemini-2.5-flash")[
            "user"
        ]
        == "another_user"
    )
