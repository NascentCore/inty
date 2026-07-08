"""Resolve user-visible assistant text from one in-turn sync tool-loop message."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.core.companion_harness.companion.dual_llm_chat_branch_envelope import (
    parse_dual_llm_chat_envelope_json,
)
from app.core.companion_harness.companion.models import user_visible_assistant_text


def _message_field(message: Any, field_name: str) -> Any:
    if isinstance(message, Mapping):
        return message.get(field_name)
    return getattr(message, field_name, None)


def _string_candidates_from_value(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, Mapping):
        out: list[str] = []
        for key in ("content", "text", "summary"):
            out.extend(_string_candidates_from_value(value.get(key)))
        return out
    if isinstance(value, (list, tuple)):
        out: list[str] = []
        for item in value:
            out.extend(_string_candidates_from_value(item))
        return out
    return []


def _assistant_message_candidate_texts(message: Any) -> list[str]:
    content_candidates = _string_candidates_from_value(
        _message_field(message, "content")
    )
    reasoning_candidates = [
        *_string_candidates_from_value(_message_field(message, "reasoning")),
        *_string_candidates_from_value(
            _message_field(message, "reasoning_details")
        ),
    ]
    return [*content_candidates, *reasoning_candidates]


def _visible_from_candidate_raw(raw: str) -> str | None:
    envelope = parse_dual_llm_chat_envelope_json(raw)
    if envelope is not None:
        return user_visible_assistant_text(envelope.user_facing_reply)
    return user_visible_assistant_text(raw)


def resolve_in_turn_assistant_visible_text(message: Any) -> str | None:
    """Return non-blank user-visible line for one in-turn assistant message, or None."""
    for raw in _assistant_message_candidate_texts(message):
        visible = _visible_from_candidate_raw(raw)
        if visible is not None:
            return visible
    return None
