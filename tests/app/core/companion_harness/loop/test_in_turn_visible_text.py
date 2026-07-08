"""Tests for in-turn visible assistant text resolution."""

from __future__ import annotations

from types import SimpleNamespace

from app.core.companion_harness.loop.in_turn_visible_text import (
    resolve_in_turn_assistant_visible_text,
)


def test_resolve_prefers_message_content() -> None:
    message = SimpleNamespace(
        content="  hello there  ",
        reasoning=None,
        reasoning_details=None,
        tool_calls=[],
    )
    assert resolve_in_turn_assistant_visible_text(message) == "hello there"


def test_resolve_reads_reasoning_side_channel() -> None:
    message = SimpleNamespace(
        content="",
        reasoning="我先帮你记一下。",
        reasoning_details=None,
        tool_calls=[{"id": "tc1"}],
    )
    assert (
        resolve_in_turn_assistant_visible_text(message)
        == "我先帮你记一下。"
    )


def test_resolve_envelope_user_facing_reply() -> None:
    message = SimpleNamespace(
        content='{"user_facing_reply":"好的，我来写档案。","importance_round":5,'
        '"importance_user_message":5,"importance_assistant_message":5,'
        '"output_to_user":true,"turn_recall":""}',
        reasoning=None,
        reasoning_details=None,
        tool_calls=[],
    )
    assert (
        resolve_in_turn_assistant_visible_text(message)
        == "好的，我来写档案。"
    )


def test_resolve_returns_none_for_blank_tool_round() -> None:
    message = SimpleNamespace(
        content="",
        reasoning="",
        reasoning_details=None,
        tool_calls=[{"id": "tc1"}],
    )
    assert resolve_in_turn_assistant_visible_text(message) is None
