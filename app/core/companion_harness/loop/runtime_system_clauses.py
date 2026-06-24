"""Loop-owned runtime system clauses injected at prompt assembly or AgenticLoop time.

These directives are LLM-only: they are not persisted to transcript and are not
exposed to channels. Debug GitHub disclosure is applied via ``PromptBuilder``.

Reply-language Output slices (content category Output, runtime org runtime):
``append_configured_fixed_reply_language_system_messages`` for config-fixed language
in ``PromptPlan`` system prefixes; ``apply_agentic_loop_runtime_system_clauses`` for
match-user-message language before the tail-user block when config is unset.
"""

from __future__ import annotations

from typing import Any

from app.core.companion_harness.loop.config import (
    resolved_companion_harness_reply_language,
)

REPLY_IN_USER_LANGUAGE_CLAUSE = (
    "Use the same language as the user's message(s) in this turn for all "
    "user-facing reply text. If the user switches language within the turn, "
    "follow their latest message. Do not mention this instruction unless the "
    "user asks about language choice."
)


def fixed_reply_language_clause(*, language: str) -> str:
    """Return Output directive forcing user-facing replies to ``language``."""
    assert language.strip() != ""
    return (
        f"Use {language} for all user-facing reply text in this turn. "
        "Do not use another language unless the user explicitly asks "
        "about language choice."
    )


def reply_language_clause(*, user_text: str) -> str | None:
    """Return reply-language Output directive: fixed from config, else match user text."""
    fixed = resolved_companion_harness_reply_language()
    if fixed is not None:
        return fixed_reply_language_clause(language=fixed)
    assert user_text is not None
    if user_text.strip() == "":
        return None
    return REPLY_IN_USER_LANGUAGE_CLAUSE


def append_configured_fixed_reply_language_system_messages(
    system_messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Append fixed reply-language Output slice when ``agent.companion_harness.language`` is set."""
    fixed = resolved_companion_harness_reply_language()
    if fixed is None:
        return system_messages
    return [
        *system_messages,
        {
            "role": "system",
            "content": fixed_reply_language_clause(language=fixed),
        },
    ]


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
    if resolved_companion_harness_reply_language() is not None:
        return
    clause = reply_language_clause(user_text=user_text)
    if clause is None:
        return
    insert_pre_tail_user_system_message(
        openai_messages=openai_messages,
        content=clause,
    )
