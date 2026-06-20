"""Tests for ``context.json`` experience directives (#3342 A3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.companion_harness.companion.models import (
    ContextMeta,
    load_context_meta,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.experience_profile.experience_directives import (
    ExperienceDirectiveTone,
    ExperienceDirectives,
    ExperienceSessionIntent,
)
from app.core.companion_harness.memory.memory_store import MemoryStore


def test_context_meta_default_experience_directives() -> None:
    meta = ContextMeta()
    assert meta.experience_directives == ExperienceDirectives()
    assert meta.experience_directives.tone is None


def test_context_meta_parses_experience_directives_tone() -> None:
    meta = ContextMeta.model_validate(
        {
            "context_mode": "intimate",
            "experience_directives": {"tone": "playful"},
        }
    )
    assert meta.experience_directives.tone == ExperienceDirectiveTone.PLAYFUL


def test_context_meta_rejects_invalid_experience_directives_tone() -> None:
    with pytest.raises(ValidationError):
        ContextMeta.model_validate(
            {
                "context_mode": "intimate",
                "experience_directives": {"tone": "not_a_tone"},
            }
        )


def test_context_meta_rejects_invalid_experience_directives_intent() -> None:
    with pytest.raises(ValidationError):
        ContextMeta.model_validate(
            {
                "context_mode": "intimate",
                "experience_directives": {"intent": "not_an_intent"},
            }
        )


def test_context_meta_accepts_matching_intent_and_context_mode() -> None:
    meta = ContextMeta.model_validate(
        {
            "context_mode": "roleplay",
            "experience_directives": {"intent": "roleplay"},
        }
    )
    assert meta.experience_directives.intent == ExperienceSessionIntent.ROLEPLAY


def test_context_meta_rejects_intent_context_mode_drift() -> None:
    with pytest.raises(ValidationError):
        ContextMeta.model_validate(
            {
                "context_mode": "roleplay",
                "experience_directives": {"intent": "casual_chat"},
            }
        )


def test_load_context_meta_repairs_intent_context_mode_drift(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("ed-drift", "a", tmp_path.name),
        repository=None,
    )
    store.write_document(
        "context.json",
        json.dumps(
            {
                "context_mode": "roleplay",
                "experience_directives": {"intent": "casual_chat"},
            },
            ensure_ascii=False,
        )
        + "\n",
    )
    meta = load_context_meta(store=store)
    assert meta.context_mode == "emotional_companion"
    assert (
        meta.experience_directives.intent == ExperienceSessionIntent.CASUAL_CHAT
    )


def test_load_context_meta_legacy_json_without_directives(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("ed", "a", tmp_path.name),
        repository=None,
    )
    store.write_document("context.json", '{"context_mode": "intimate"}\n')
    meta = load_context_meta(store=store)
    assert meta.experience_directives.tone is None


def test_experience_directives_system_clause_none_when_unset() -> None:
    from app.core.companion_harness.experience_profile.experience_directives import (
        experience_directives_system_clause,
    )

    assert experience_directives_system_clause(ExperienceDirectives()) is None


def test_experience_directives_system_clause_playful() -> None:
    from app.core.companion_harness.experience_profile.experience_directives import (
        EXPERIENCE_DIRECTIVES_SYSTEM_HEADING,
        experience_directives_system_clause,
    )

    out = experience_directives_system_clause(
        ExperienceDirectives(
            intent=ExperienceSessionIntent.CASUAL_CHAT,
            tone=ExperienceDirectiveTone.PLAYFUL,
        )
    )
    assert out is not None
    assert out.startswith(EXPERIENCE_DIRECTIVES_SYSTEM_HEADING)
    assert "casual_chat" in out
    assert "playful" in out
    assert "俏皮" in out
