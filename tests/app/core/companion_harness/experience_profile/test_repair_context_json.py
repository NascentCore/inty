"""Tests for context.json drift repair before ContextMeta validation."""

from __future__ import annotations

from app.core.companion_harness.experience_profile.experience_directives import (
    repair_context_json_dict,
)


def test_repair_context_json_dict_aligns_context_mode_to_intent() -> None:
    repaired = repair_context_json_dict(
        {
            "context_mode": "roleplay",
            "experience_directives": {"intent": "casual_chat"},
        }
    )
    assert repaired["context_mode"] == "emotional_companion"


def test_repair_context_json_dict_noop_when_intent_unset() -> None:
    raw = {"context_mode": "roleplay", "experience_directives": {}}
    assert repair_context_json_dict(raw) == raw
