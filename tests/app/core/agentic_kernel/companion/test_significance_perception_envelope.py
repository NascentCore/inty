from __future__ import annotations

import json

from app.core.agentic_kernel.companion.significance_perception import (
    parse_dual_llm_chat_envelope_json,
    split_dual_llm_chat_branch_content,
)


def _envelope_dict() -> dict:
    return {
        "user_facing_reply": "hello",
        "importance_round": 5,
        "importance_user_message": 4,
        "importance_assistant_message": 6,
        "output_to_user": True,
    }


def test_parse_dual_llm_chat_envelope_accepts_markdown_json_fence() -> None:
    inner = json.dumps(_envelope_dict(), ensure_ascii=False)
    raw = f"```json\n{inner}\n```"
    env = parse_dual_llm_chat_envelope_json(raw)
    assert env is not None
    assert env.user_facing_reply == "hello"
    assert env.importance_round == 5


def test_split_dual_llm_chat_branch_content_strips_fence_and_returns_meta() -> None:
    inner = json.dumps(_envelope_dict(), ensure_ascii=False)
    text, meta, o2u = split_dual_llm_chat_branch_content(f"```\n{inner}\n```")
    assert text == "hello"
    assert meta == {
        "importance_round": 5,
        "importance_user_message": 4,
        "importance_assistant_message": 6,
    }
    assert o2u is True


def test_parse_dual_llm_chat_envelope_invalid_inside_fence_returns_none() -> None:
    assert parse_dual_llm_chat_envelope_json("```json\nnot json\n```") is None
