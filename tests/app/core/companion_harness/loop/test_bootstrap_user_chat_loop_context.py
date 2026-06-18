"""Tests for ``build_bootstrap_user_chat_loop_context`` in ``loop/context.py``."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    InnerTickActivity,
)
from app.core.companion_harness.llm.langsmith_invocation_extra import (
    SOURCE_BOOTSTRAP_TRACK,
)
from app.core.companion_harness.loop.context import (
    build_bootstrap_user_chat_loop_context,
)
from app.core.companion_harness.tools.companion_tool_definitions import (
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
)

from tests.app.core.companion_harness.loop.context_builder_test_support import (
    base_user_chat_loop_builder_kwargs,
)


def test_bootstrap_loop_context_passes_openai_dict_messages() -> None:
    """``turn.py`` passes ``CompanionTurnPromptPlan.messages`` (OpenAI dicts) into the bootstrap builder."""
    openai_messages = [
        {"role": "system", "content": "bootstrap sys"},
        {"role": "user", "content": "hello"},
    ]
    kwargs = base_user_chat_loop_builder_kwargs()
    kwargs["messages"] = openai_messages

    context = build_bootstrap_user_chat_loop_context(
        **kwargs,
        after_tool_messages_appended=MagicMock(),
    )

    assert context.openai_messages == tuple(openai_messages)


def test_bootstrap_loop_context_uses_bootstrap_track_and_allowlist() -> None:
    kwargs = base_user_chat_loop_builder_kwargs()
    kwargs["messages"] = [{"role": "user", "content": "hi"}]
    kwargs["stack_depth"] = 0
    kwargs["langsmith_trace_id"] = ""
    kwargs["langsmith_run_id"] = ""
    context = build_bootstrap_user_chat_loop_context(
        **kwargs,
        after_tool_messages_appended=MagicMock(),
    )

    assert context.write_allowlist == MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP
    assert context.langsmith.foreground_source == SOURCE_BOOTSTRAP_TRACK
    assert context.inner_tick_activity == InnerTickActivity.MAINTENANCE
    assert context.companion_turn_track == CompanionTurnTrack.USER_CHAT_BOOTSTRAP
