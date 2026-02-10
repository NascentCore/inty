"""
端到端测试：最小化 Role Play 示例（组装 + 可选真实 API 一轮对话）。
CREATED_BY_AGENT
"""

from __future__ import annotations

import os

import pytest

from experimental.agentic_ai_companion.role_play_minimal import build_system_messages_openai


def test_build_system_messages_openai_count_and_roles() -> None:
    """组装结果应为 2 条系统消息。"""
    messages = build_system_messages_openai(char_name="小艾", user_name="User")
    assert len(messages) == 2
    for m in messages:
        assert m["role"] == "system"
        assert isinstance(m["content"], str)
        assert len(m["content"]) > 0


def test_build_system_messages_openai_template_rendered() -> None:
    """{{char}} / {{user}} 已被替换，且包含渲染后的主/模式片段。"""
    char_name = "TestChar"
    user_name = "TestUser"
    messages = build_system_messages_openai(char_name=char_name, user_name=user_name)
    combined = " ".join(m["content"] for m in messages)
    assert "{{char}}" not in combined
    assert "{{user}}" not in combined
    assert char_name in combined
    assert user_name in combined
    assert "Purity" in combined or "purity" in combined or "engaging" in combined


@pytest.mark.slow
def test_role_play_minimal_one_turn_e2e() -> None:
    """具备 OPENROUTER_API_KEY 或 OPENAI_API_KEY 时调用真实 API 完成一轮对话。"""
    if not (os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")):
        pytest.skip("需要 OPENROUTER_API_KEY 或 OPENAI_API_KEY 以运行真实 API 测试")
    from experimental.agentic_ai_companion.role_play_minimal import (
        create_openai_client,
        get_default_model,
    )
    from openai import OpenAI

    system_messages = build_system_messages_openai(char_name="小艾", user_name="User")
    client: OpenAI = create_openai_client()
    model = get_default_model()
    messages: list[dict[str, str]] = [
        *system_messages,
        {"role": "user", "content": "你好，今天天气不错。"},
    ]
    resp = client.chat.completions.create(model=model, messages=messages)
    content = resp.choices[0].message.content
    assert content is not None
    assert len(content.strip()) > 0
    assert resp.choices[0].message.role == "assistant"
