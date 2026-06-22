"""Unit tests for proactive inner-tick structured output envelope."""

from __future__ import annotations

import json

from app.core.companion_harness.companion.proactive_chat_envelope import (
    PROACTIVE_CHAT_RESPONSE_FORMAT,
    ProactiveChatEnvelope,
    _build_proactive_chat_response_format,
    parse_proactive_chat_envelope_from_message,
    parse_proactive_chat_envelope_json,
    split_proactive_chat_message,
)
import pytest
from pydantic import ValidationError


def test_proactive_envelope_output_to_user_true_requires_message() -> None:
    env = ProactiveChatEnvelope(output_to_user=True, message="hey")
    assert env.message == "hey"


def test_proactive_envelope_output_to_user_false_requires_empty_message() -> (
    None
):
    env = ProactiveChatEnvelope(output_to_user=False, message="")
    assert env.output_to_user is False


def test_proactive_envelope_rejects_true_with_empty_message() -> None:
    with pytest.raises(ValidationError):
        ProactiveChatEnvelope(output_to_user=True, message="")


def test_proactive_envelope_rejects_false_with_message() -> None:
    with pytest.raises(ValidationError):
        ProactiveChatEnvelope(output_to_user=False, message="nope")


def test_parse_proactive_chat_envelope_json_garbage_returns_none() -> None:
    assert parse_proactive_chat_envelope_json("not json") is None


def test_split_proactive_chat_message_fail_closed_on_garbage() -> None:
    split = split_proactive_chat_message({"content": "plain text only"})
    assert split.output_to_user is False
    assert split.visible_text == ""


def test_split_proactive_chat_message_output_to_user_false() -> None:
    inner = json.dumps({"output_to_user": False, "message": ""})
    split = split_proactive_chat_message({"content": inner})
    assert split.output_to_user is False
    assert split.visible_text == ""


def test_split_proactive_chat_message_output_to_user_true() -> None:
    inner = json.dumps({"output_to_user": True, "message": "  hello  "})
    split = split_proactive_chat_message({"content": inner})
    assert split.output_to_user is True
    assert split.visible_text == "hello"


def test_split_proactive_chat_message_reads_reasoning_side_channel() -> None:
    inner = json.dumps({"output_to_user": True, "message": "from reasoning"})
    message = {"content": None, "reasoning": inner}
    split = split_proactive_chat_message(message)
    assert split.visible_text == "from reasoning"
    env = parse_proactive_chat_envelope_from_message(message)
    assert env is not None
    assert env.message == "from reasoning"


def test_proactive_response_format_constant_matches_builder() -> None:
    assert (
        PROACTIVE_CHAT_RESPONSE_FORMAT
        == _build_proactive_chat_response_format()
    )
