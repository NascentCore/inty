"""Build path for ``record_user_feedback`` rows (validation + repro context, no DB I/O)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.tools.user_feedback import (
    build_companion_user_feedback,
)


def test_build_companion_user_feedback_captures_scope_and_repro_context() -> None:
    row = build_companion_user_feedback(
        scope=CompanionScope("user-1", "agent-1", "chat-1"),
        trace_id="trace-abc",
        user_msg_uuid="umsg-9",
        arguments={
            "category": "talks_too_much",
            "feedback_text": "User keeps saying replies are too long.",
            "user_quote": "you are talking too much",
            "offending_assistant_text": "...a very long reply...",
        },
    )
    assert row.user_id == "user-1"
    assert row.companion_id == "agent-1"
    assert row.chat_id == "chat-1"
    assert row.category == "talks_too_much"
    assert row.trace_id == "trace-abc"
    assert row.user_msg_uuid == "umsg-9"
    assert row.repro_context == {
        "user_quote": "you are talking too much",
        "offending_assistant_text": "...a very long reply...",
    }
    assert len(row.id) == 32


def test_build_companion_user_feedback_rejects_unknown_category() -> None:
    with pytest.raises(ValidationError):
        build_companion_user_feedback(
            scope=CompanionScope("u", "a", "c"),
            trace_id=None,
            user_msg_uuid=None,
            arguments={"category": "bogus", "feedback_text": "x"},
        )


def test_build_companion_user_feedback_rejects_empty_feedback_text() -> None:
    with pytest.raises(ValidationError):
        build_companion_user_feedback(
            scope=CompanionScope("u", "a", "c"),
            trace_id=None,
            user_msg_uuid=None,
            arguments={"category": "other", "feedback_text": "   "},
        )
