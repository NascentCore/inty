"""Tests for loop-owned runtime system clauses."""

from __future__ import annotations

from typing import Any

from app.core.companion_harness.companion.prompt_stack import (
    replace_leading_system_messages_inplace,
)
from app.core.companion_harness.loop.runtime_system_clauses import (
    REPLY_IN_USER_LANGUAGE_CLAUSE,
    apply_agentic_loop_runtime_system_clauses,
    reply_in_user_language_system_clause,
)


def _realistic_message_stack() -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": "doctrine"},
        {"role": "system", "content": "persona"},
        {"role": "user", "content": "earlier user"},
        {"role": "assistant", "content": "earlier assistant"},
        {"role": "system", "content": "## User's Local Time Context"},
        {"role": "user", "content": "你好"},
    ]


def test_reply_in_user_language_system_clause_skips_empty_user_text() -> None:
    assert reply_in_user_language_system_clause(user_text="") is None
    assert reply_in_user_language_system_clause(user_text="   ") is None


def test_apply_inserts_clause_after_time_context_before_tail_user() -> None:
    messages = _realistic_message_stack()
    apply_agentic_loop_runtime_system_clauses(
        openai_messages=messages,
        user_text="你好",
    )
    assert messages == [
        {"role": "system", "content": "doctrine"},
        {"role": "system", "content": "persona"},
        {"role": "user", "content": "earlier user"},
        {"role": "assistant", "content": "earlier assistant"},
        {"role": "system", "content": "## User's Local Time Context"},
        {"role": "system", "content": REPLY_IN_USER_LANGUAGE_CLAUSE},
        {"role": "user", "content": "你好"},
    ]
    clause_rows = [
        row
        for row in messages
        if row.get("role") == "system"
        and row.get("content") == REPLY_IN_USER_LANGUAGE_CLAUSE
    ]
    assert len(clause_rows) == 1


def test_apply_inserts_before_multi_tail_user_rows() -> None:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": "prefix"},
        {"role": "user", "content": "history"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "first batch line"},
        {"role": "user", "content": "second batch line"},
    ]
    apply_agentic_loop_runtime_system_clauses(
        openai_messages=messages,
        user_text="first batch line",
    )
    assert messages[3] == {
        "role": "system",
        "content": REPLY_IN_USER_LANGUAGE_CLAUSE,
    }
    assert messages[4]["content"] == "first batch line"
    assert messages[5]["content"] == "second batch line"


def test_clause_survives_leading_prefix_refresh() -> None:
    messages = _realistic_message_stack()
    apply_agentic_loop_runtime_system_clauses(
        openai_messages=messages,
        user_text="你好",
    )
    replace_leading_system_messages_inplace(
        messages,
        [
            {"role": "system", "content": "refreshed doctrine"},
            {"role": "system", "content": "refreshed persona"},
        ],
    )
    clause_rows = [
        row
        for row in messages
        if row.get("role") == "system"
        and row.get("content") == REPLY_IN_USER_LANGUAGE_CLAUSE
    ]
    assert len(clause_rows) == 1
    assert messages[-2]["content"] == REPLY_IN_USER_LANGUAGE_CLAUSE
    assert messages[-1]["content"] == "你好"
