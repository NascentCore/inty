"""Tests for ``build_bootstrap_user_chat_loop_context`` in ``loop/context.py``."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
)
from app.core.companion_harness.llm.langsmith_invocation_extra import (
    LangsmithLlmSource,
)
from app.core.companion_harness.loop.context import (
    build_bootstrap_user_chat_loop_context,
)
from app.core.companion_harness.prompt_builder import (
    PromptMessage,
    PromptMessageRole,
    PromptPlan,
)
from app.core.companion_harness.tools.companion_tool_definitions import (
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
)

from tests.app.core.companion_harness.loop.context_builder_test_support import (
    base_user_chat_loop_builder_kwargs,
    loop_execution_for_track,
)


def _bootstrap_prompt_plan() -> PromptPlan:
    return PromptPlan(
        messages=(
            PromptMessage(
                role=PromptMessageRole.SYSTEM, content="bootstrap sys"
            ),
            PromptMessage(role=PromptMessageRole.USER, content="hello"),
        ),
        tools=(),
        tool_choice=None,
    )


def test_bootstrap_loop_context_passes_openai_dict_messages() -> None:
    """``turn.py`` still passes legacy ``messages`` for correlation; execution uses ``prompt_plan``."""
    openai_messages = [
        {"role": "system", "content": "bootstrap sys"},
        {"role": "user", "content": "hello"},
    ]
    kwargs = base_user_chat_loop_builder_kwargs()
    kwargs["messages"] = openai_messages
    prompt_plan = _bootstrap_prompt_plan()

    context = build_bootstrap_user_chat_loop_context(
        **kwargs,
        after_tool_messages_appended=MagicMock(),
        prompt_plan=prompt_plan,
        execution=loop_execution_for_track(
            track=CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
            user_text="hello",
            has_openai_tools=False,
        ),
    )

    assert context.openai_messages == tuple(openai_messages)
    assert context.prompt_plan is prompt_plan


def test_bootstrap_loop_context_uses_bootstrap_track_and_allowlist() -> None:
    kwargs = base_user_chat_loop_builder_kwargs()
    kwargs["messages"] = [{"role": "user", "content": "hi"}]
    kwargs["stack_depth"] = 0
    kwargs["langsmith_trace_id"] = ""
    kwargs["langsmith_run_id"] = ""
    prompt_plan = _bootstrap_prompt_plan()
    context = build_bootstrap_user_chat_loop_context(
        **kwargs,
        after_tool_messages_appended=MagicMock(),
        prompt_plan=prompt_plan,
        execution=loop_execution_for_track(
            track=CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
            user_text="hi",
            has_openai_tools=False,
        ),
    )

    execution = context.execution
    assert (
        execution.write_allowlist
        == MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP
    )
    assert execution.foreground_source == LangsmithLlmSource.BOOTSTRAP_TRACK
    assert (
        context.companion_turn_track == CompanionTurnTrack.USER_CHAT_BOOTSTRAP
    )
    assert context.prompt_plan is prompt_plan
