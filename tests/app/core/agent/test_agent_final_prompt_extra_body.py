# 测试 Agent.get_final_prompt 与 Agent._chat_extra_body（review 增强补充）
from app.core.agent.agent import Agent


def _minimal_agent(**kwargs) -> Agent:
    """构建最小 Agent，仅传必要参数与待测字段。"""
    return Agent(
        agent_id=kwargs.get("agent_id", "test-agent"),
        name=kwargs.get("name", "Test"),
        model_config=kwargs.get("model_config", {}),
        **{k: v for k, v in kwargs.items() if k not in ("agent_id", "name", "model_config")},
    )


def test_chat_extra_body_returns_expected_dict():
    """_chat_extra_body 返回 generation_config.thinking_budget 与 user。"""
    agent = _minimal_agent()
    got = agent._chat_extra_body("user_123")
    assert got == {
        "generation_config": {"thinking_budget": 0},
        "user": "user_123",
    }


def test_chat_extra_body_different_user_id():
    """_chat_extra_body 的 user 字段与传入的 user_id 一致。"""
    agent = _minimal_agent()
    assert agent._chat_extra_body("another_user")["user"] == "another_user"


def test_get_final_prompt_returns_combined_prompt_when_set(monkeypatch):
    """当 main/mode/personality 有自定义内容时，get_final_prompt 返回组合结果。"""
    from app.core.agent import agent as agent_module

    monkeypatch.setattr(
        agent_module.global_config_loaded_from_config_yaml.agent,
        "force_default_prompts",
        False,
    )
    monkeypatch.setattr(
        agent_module,
        "get_agent_prompt_override",
        lambda _id, _name: None,
    )

    agent = _minimal_agent(
        main_prompt="CustomMain",
        mode_prompt="CustomMode",
        personality="CustomPersonality",
    )
    result = agent.get_final_prompt()
    assert "CustomMain" in result
    assert "[角色性格]\nCustomPersonality" in result
    assert "CustomMode" in result
    assert result.startswith("CustomMain")
    assert result.endswith("CustomMode")


def test_get_final_prompt_returns_ai_assistant_when_all_empty(monkeypatch):
    """当 effective main/mode 与 personality 均为空时，返回「AI助手」。"""
    from app.core.agent import agent as agent_module

    monkeypatch.setattr(
        agent_module.global_config_loaded_from_config_yaml.agent,
        "force_default_prompts",
        False,
    )
    monkeypatch.setattr(
        agent_module,
        "get_agent_prompt_override",
        lambda _id, _name: None,
    )
    # 使 effective main/mode 为空：自定义字符串且 get_*_by_id 报错会返回原串，故用空串
    agent = _minimal_agent(
        main_prompt="",
        mode_prompt="",
        personality="",
    )
    # 无 main 时 _get_effective_main_prompt 会回退到 ROMANTIC default，需把默认也打成空
    monkeypatch.setattr(
        agent,
        "_get_effective_main_prompt",
        lambda: "",
    )
    monkeypatch.setattr(
        agent,
        "_get_effective_mode_prompt",
        lambda: "",
    )
    assert agent.get_final_prompt() == "AI助手"


def test_get_final_prompt_personality_only(monkeypatch):
    """仅有 personality 时，get_final_prompt 只包含角色性格段。"""
    from app.core.agent import agent as agent_module

    monkeypatch.setattr(
        agent_module.global_config_loaded_from_config_yaml.agent,
        "force_default_prompts",
        False,
    )
    monkeypatch.setattr(
        agent_module,
        "get_agent_prompt_override",
        lambda _id, _name: None,
    )
    agent = _minimal_agent(
        main_prompt="",
        mode_prompt="",
        personality="OnlyPersonality",
    )
    monkeypatch.setattr(agent, "_get_effective_main_prompt", lambda: "")
    monkeypatch.setattr(agent, "_get_effective_mode_prompt", lambda: "")
    result = agent.get_final_prompt()
    assert result == "[角色性格]\nOnlyPersonality"
