"""Loop-owned runtime system clauses injected at AgenticLoop execution time.

These directives are LLM-only: they are not assembled by PromptBuilder, not
persisted to transcript, and not exposed to channels or upper-layer turn code.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class LoopRuntimeSystemClauseKind(StrEnum):
    """Semantic kinds of harness-internal system text owned by AgenticLoop."""

    REPLY_IN_USER_LANGUAGE = "reply_in_user_language"


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
