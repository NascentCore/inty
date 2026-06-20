from __future__ import annotations

import json

from app.core.companion_harness.companion.dual_llm_chat_branch_envelope import (
    parse_dual_llm_chat_envelope_from_message,
    parse_dual_llm_chat_envelope_json,
    split_dual_llm_chat_branch_content,
    split_dual_llm_chat_branch_message,
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


def test_split_dual_llm_chat_branch_content_strips_fence_and_returns_meta() -> (
    None
):
    inner = json.dumps(_envelope_dict(), ensure_ascii=False)
    split = split_dual_llm_chat_branch_content(f"```\n{inner}\n```")
    assert split.visible_text == "hello"
    assert split.significance_meta == {
        "importance_round": 5,
        "importance_user_message": 4,
        "importance_assistant_message": 6,
    }
    assert split.output_to_user is True


def test_split_dual_llm_chat_branch_message_reads_reasoning_envelope() -> None:
    inner = json.dumps(_envelope_dict(), ensure_ascii=False)
    message = {
        "content": None,
        "reasoning": inner,
    }
    split = split_dual_llm_chat_branch_message(message)
    assert split.visible_text == "hello"
    assert split.significance_meta == {
        "importance_round": 5,
        "importance_user_message": 4,
        "importance_assistant_message": 6,
    }
    assert split.output_to_user is True


def test_parse_dual_llm_chat_envelope_from_message_reads_reasoning_details() -> (
    None
):
    inner = json.dumps(_envelope_dict(), ensure_ascii=False)
    message = {
        "content": None,
        "reasoning_details": [{"type": "text", "text": inner}],
    }
    env = parse_dual_llm_chat_envelope_from_message(message)
    assert env is not None
    assert env.user_facing_reply == "hello"


def test_split_dual_llm_chat_branch_message_ignores_non_json_reasoning() -> (
    None
):
    message = {
        "content": None,
        "reasoning": "private reasoning, not a JSON envelope",
    }
    split = split_dual_llm_chat_branch_message(message)
    assert split.visible_text == ""
    assert split.significance_meta is None
    assert split.output_to_user is None


def test_parse_dual_llm_chat_envelope_invalid_inside_fence_returns_none() -> (
    None
):
    assert parse_dual_llm_chat_envelope_json("```json\nnot json\n```") is None
