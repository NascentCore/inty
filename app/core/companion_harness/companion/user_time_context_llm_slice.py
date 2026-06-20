"""Companion-local user wall-clock facts for one LLM turn.

Delegates line formatting to :mod:`app.core.user_time_context_llm_meta` so the
harness ``## user-time-context`` **system** slice matches the classic agent
tail-user suffix contract.

# TODO(code-structure): Move this to app.core.companion_harness.companion.prompts.user_time_context_slice.py — #3409


TODO(companion-package-reorg): Move this module into a focused sub-package under companion_harness (see issue body for draft layout). — #3409
https://github.com/NascentCore/inty/issues/3409"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.core.user_time_context_llm_meta import (
    build_user_time_context_meta_lines,
)

USER_TIME_CONTEXT_SYSTEM_HEADER = "## User's Local Time Context"


def build_companion_user_time_context_system_content(
    user_time_context: Mapping[str, Any] | None,
    *,
    enabled: bool,
) -> str | None:
    """Return one system message body, or ``None`` when nothing should be injected.

    First line is ``USER_TIME_CONTEXT_SYSTEM_HEADER``; following lines are
    ``User's time:`` / ``Time zone:`` when the corresponding fields are present
    (blank fields omitted).
    """
    if not enabled or not user_time_context:
        return None
    meta_lines = build_user_time_context_meta_lines(user_time_context)
    if not meta_lines:
        return None
    return USER_TIME_CONTEXT_SYSTEM_HEADER + "\n" + "\n".join(meta_lines)
