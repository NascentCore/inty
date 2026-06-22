"""Loop-owned runtime system clauses injected at prompt assembly or AgenticLoop time.

These directives are LLM-only: they are not persisted to transcript and are not
exposed to channels. Debug GitHub disclosure is applied via ``PromptBuilder``;
reply-language clauses are applied via ``AgenticLoop``.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class LoopRuntimeSystemClauseKind(StrEnum):
    """Semantic kinds of harness-internal system text owned by AgenticLoop."""

    REPLY_IN_USER_LANGUAGE = "reply_in_user_language"
    DEBUG_DISCLOSE_GITHUB_ISSUE = "debug_disclose_github_issue"


REPLY_IN_USER_LANGUAGE_CLAUSE = (
    "Use the same language as the user's message(s) in this turn for all "
    "user-facing reply text. If the user switches language within the turn, "
    "follow their latest message. Do not mention this instruction unless the "
    "user asks about language choice."
)


def reply_in_user_language_system_clause(*, user_text: str) -> str | None:
    """Return reply-language directive when the turn carries user text."""
    assert user_text is not None
    if user_text.strip() == "":
        return None
    return REPLY_IN_USER_LANGUAGE_CLAUSE


DEBUG_DISCLOSE_GITHUB_ISSUE_CLAUSE = (
    "Debug disclosure (local testing only): when you call "
    "companion_record_user_feedback and the tool return contains "
    "github_issue_url=..., set output_to_user to true and include that exact URL "
    "in user_facing_reply for the user-visible follow-up. Do not invent URLs; "
    "only copy from the tool return. Keep an empathetic tone."
)


def debug_disclose_github_issue_system_clause() -> str | None:
    """Return debug GitHub disclosure directive when ``app.debug`` disclosure is on."""
    from app.core.companion_harness.tools.companion_user_feedback import (
        UserFeedbackDisclosureMode,
        resolve_user_feedback_disclosure_mode,
    )

    if (
        resolve_user_feedback_disclosure_mode()
        != UserFeedbackDisclosureMode.VISIBLE
    ):
        return None
    return DEBUG_DISCLOSE_GITHUB_ISSUE_CLAUSE


def apply_debug_github_disclosure_runtime_clause(
    *,
    openai_messages: list[dict[str, Any]],
) -> None:
    """Insert debug GitHub disclosure clause before the trailing tail-user block."""
    clause = debug_disclose_github_issue_system_clause()
    if clause is None:
        return
    insert_pre_tail_user_system_message(
        openai_messages=openai_messages,
        content=clause,
    )


def insert_pre_tail_user_system_message(
    *,
    openai_messages: list[dict[str, Any]],
    content: str,
) -> None:
    """Insert one system row immediately before the trailing tail-user block."""
    tail_user_count = 0
    index = len(openai_messages) - 1
    while index >= 0 and openai_messages[index].get("role") == "user":
        tail_user_count += 1
        index -= 1
    assert tail_user_count >= 1
    insertion_index = len(openai_messages) - tail_user_count
    openai_messages.insert(
        insertion_index,
        {"role": "system", "content": content},
    )


def apply_agentic_loop_runtime_system_clauses(
    *,
    openai_messages: list[dict[str, Any]],
    user_text: str,
) -> None:
    """Inject loop runtime system clauses once before the first LLM call."""
    clause = reply_in_user_language_system_clause(user_text=user_text)
    if clause is None:
        return
    insert_pre_tail_user_system_message(
        openai_messages=openai_messages,
        content=clause,
    )
