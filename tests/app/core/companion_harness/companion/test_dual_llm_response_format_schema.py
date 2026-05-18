"""Contract tests for dual-LLM ``response_format`` and envelope parsing (baseline + post-refactor)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.companion_harness.companion.dual_llm_chat_branch_envelope import (
    DUAL_LLM_CHAT_RESPONSE_FORMAT,
    _build_dual_llm_chat_response_format,
    parse_dual_llm_chat_envelope_json,
    split_dual_llm_chat_branch_message,
)


def _envelope_payload() -> dict[str, Any]:
    return {
        "user_facing_reply": "visible",
        "importance_round": 3,
        "importance_user_message": 2,
        "importance_assistant_message": 4,
        "output_to_user": True,
        "reply_modality": "text",
        "voice_message_script": "",
    }


def assert_dual_llm_response_format_schema_contract(fmt: dict[str, Any]) -> None:
    """Wire shape expected by OpenRouter/OpenAI ``json_schema`` + strict companion envelope."""
    assert fmt["type"] == "json_schema"
    js = fmt["json_schema"]
    assert js["name"] == "companion_dual_llm_chat_envelope"
    assert js["strict"] is True
    schema = js["schema"]
    assert schema["type"] == "object"
    assert schema.get("additionalProperties") is False
    props = schema["properties"]
    expected_keys = {
        "user_facing_reply",
        "importance_round",
        "importance_user_message",
        "importance_assistant_message",
        "output_to_user",
        "reply_modality",
        "voice_message_script",
    }
    assert set(props) == expected_keys
    req = schema["required"]
    assert set(req) == expected_keys
    assert len(req) == len(expected_keys)

    assert props["user_facing_reply"]["type"] == "string"
    assert "description" in props["user_facing_reply"]
    for key in (
        "importance_round",
        "importance_user_message",
        "importance_assistant_message",
    ):
        assert props[key]["type"] == "integer"
        assert props[key]["minimum"] == 1
        assert props[key]["maximum"] == 10
    assert props["output_to_user"]["type"] == "boolean"
    assert props["reply_modality"]["type"] == "string"
    assert props["reply_modality"]["enum"] == ["text", "voice_message"]
    assert props["voice_message_script"]["type"] == "string"


def test_dual_llm_chat_response_format_schema_contract() -> None:
    assert_dual_llm_response_format_schema_contract(DUAL_LLM_CHAT_RESPONSE_FORMAT)


def test_dual_llm_response_format_module_constant_matches_builder() -> None:
    assert DUAL_LLM_CHAT_RESPONSE_FORMAT == _build_dual_llm_chat_response_format()


def test_dual_llm_response_format_json_roundtrip() -> None:
    dumped = json.dumps(DUAL_LLM_CHAT_RESPONSE_FORMAT)
    assert json.loads(dumped) == DUAL_LLM_CHAT_RESPONSE_FORMAT


def test_parse_dual_llm_chat_envelope_json_accepts_plain_json() -> None:
    raw = json.dumps(_envelope_payload(), ensure_ascii=False)
    env = parse_dual_llm_chat_envelope_json(raw)
    assert env is not None
    assert env.user_facing_reply == "visible"
    assert env.importance_round == 3


def test_split_dual_llm_chat_branch_message_reads_content_envelope() -> None:
    inner = json.dumps(_envelope_payload(), ensure_ascii=False)
    msg = SimpleNamespace(content=inner, reasoning=None, reasoning_details=None)
    split = split_dual_llm_chat_branch_message(msg)
    assert split.visible_text == "visible"
    assert split.significance_meta == {
        "importance_round": 3,
        "importance_user_message": 2,
        "importance_assistant_message": 4,
    }
    assert split.output_to_user is True
    assert split.reply_modality == "text"


def test_split_dual_llm_chat_branch_message_json_fence_in_content() -> None:
    inner = json.dumps(_envelope_payload(), ensure_ascii=False)
    fenced = f"```json\n{inner}\n```"
    msg = SimpleNamespace(content=fenced, reasoning=None, reasoning_details=None)
    split = split_dual_llm_chat_branch_message(msg)
    assert split.visible_text == "visible"
    assert split.significance_meta is not None


@pytest.mark.parametrize(
    "reasoning_details",
    [
        [{"type": "text", "text": json.dumps(_envelope_payload(), ensure_ascii=False)}],
        (
            {
                "type": "reasoning.text",
                "text": json.dumps(_envelope_payload(), ensure_ascii=False),
            },
        ),
    ],
)
def test_split_dual_llm_chat_branch_message_reasoning_details_variants(
    reasoning_details: list | tuple,
) -> None:
    msg = SimpleNamespace(
        content="",
        reasoning=None,
        reasoning_details=list(reasoning_details),
    )
    split = split_dual_llm_chat_branch_message(msg)
    assert split.visible_text == "visible"
    assert split.significance_meta is not None
