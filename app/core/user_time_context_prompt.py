"""User local time context for LLM requests.

Classic Agent appends a short factual tail to the **last user** message (see
``suffix_user_text_with_time_context_lines``) when
``experimental_enable_chat_with_user_time_context`` is enabled, instead of injecting a
long system block. Line text matches :mod:`app.core.user_time_context_llm_meta`.
"""

from __future__ import annotations

from typing import Any, Mapping

from app.core.user_time_context_llm_meta import build_user_time_context_meta_lines


def suffix_user_text_with_time_context_lines(
    user_text: str,
    user_time_context: Mapping[str, Any] | None,
    *,
    enabled: bool,
) -> str:
    """Append ``User's time:`` / ``Time zone:`` lines after ``user_text`` when enabled.

    When ``enabled`` is false, or ``user_time_context`` is empty, or no field yields a
    line, returns ``user_text`` unchanged. A blank line separates the body from the
    suffix block; suffix lines use single ``\\n`` between them.
    """
    if not enabled or not user_time_context:
        return user_text

    meta_lines = build_user_time_context_meta_lines(user_time_context)
    if not meta_lines:
        return user_text

    return f"{user_text}\n\n" + "\n".join(meta_lines)
