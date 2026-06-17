"""Tests for ``loop/context.py`` builders."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.output_queue import OutputQueue
from app.core.companion_harness.agentic_companion.types import UserMessageBatch
from app.core.companion_harness.companion.langsmith_turn_slice import (
    CompanionTurnLangsmithSlice,
)
from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    ContextMeta,
    InnerTickActivity,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)
from app.core.companion_harness.llm.langsmith_invocation_extra import (
    SOURCE_BOOTSTRAP_TRACK,
    SOURCE_FOREGROUND_DUAL_LLM_ENVELOPE,
    SOURCE_SINGLE_COMPLETION,
)
from app.core.companion_harness.loop.config import (
    UserTurnLlmLoopMode,
    resolved_user_turn_llm_loop_mode,
)
from app.core.companion_harness.loop.context import (
    build_bootstrap_user_chat_loop_context,
    build_settled_dual_llm_user_chat_loop_context,
    build_settled_user_chat_loop_context,
)
from app.core.companion_harness.tools.companion_tool_definitions import (
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST_BOOTSTRAP,
)
from app.core.companion_harness.prompting.bundle import PromptBundle


def _runtime() -> TurnRuntimeContext:
    return TurnRuntimeContext(
        channel=CompanionRuntimeChannel.APP,
        implicit_signal_bundle=None,
    )


def _langsmith_slice() -> CompanionTurnLangsmithSlice:
    return CompanionTurnLangsmithSlice.from_runtime_context(_runtime())


def _output_queue() -> OutputQueue:
    return OutputQueue(scope=AgentScope(user_id="u1", agent_id="a1"))


def _batch() -> UserMessageBatch:
    return UserMessageBatch(batch_id="batch-1", message_ids=("input-1",))


def _base_builder_kwargs() -> dict:
    return {
        "messages": [{"role": "user", "content": "hi"}],
        "tools_for_turn": [],
        "repository_only_store_text": False,
        "trace_id": "trace-1",
        "user_text": "hi",
        "ts_user": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "user_msg_uuid": "user-msg-1",
        "transcript_rel": "transcript.jsonl",
        "langsmith_slice": _langsmith_slice(),
        "runtime_context": _runtime(),
        "memory_bootstrap_type": "user_interactive",
        "stack_depth": 1,
        "langsmith_trace_id": "ls-1",
        "langsmith_run_id": "run-1",
        "output_queue": _output_queue(),
        "user_message_batch": _batch(),
    }


def test_settled_user_chat_loop_context_uses_single_completion_source() -> None:
    context = build_settled_user_chat_loop_context(
        **_base_builder_kwargs(),
        after_tool_messages_appended=MagicMock(),
    )

    assert context.write_allowlist == MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST
    assert context.langsmith.foreground_source == SOURCE_SINGLE_COMPLETION
    assert context.companion_turn_track == CompanionTurnTrack.USER_CHAT


def test_bootstrap_loop_context_passes_openai_dict_messages() -> None:
    """``turn.py`` passes ``CompanionTurnPromptPlan.messages`` (OpenAI dicts) into the bootstrap builder."""
    openai_messages = [
        {"role": "system", "content": "bootstrap sys"},
        {"role": "user", "content": "hello"},
    ]
    kwargs = _base_builder_kwargs()
    kwargs["messages"] = openai_messages

    context = build_bootstrap_user_chat_loop_context(
        **kwargs,
        after_tool_messages_appended=MagicMock(),
    )

    assert context.openai_messages == tuple(openai_messages)


def test_bootstrap_loop_context_uses_bootstrap_track_and_allowlist() -> None:
    kwargs = _base_builder_kwargs()
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


def test_settled_dual_llm_context_packages_prebuilt_stacks() -> None:
    chat_msgs = ({"role": "user", "content": "hi"},)
    tool_msgs = ({"role": "user", "content": "hi"},)

    context = build_settled_dual_llm_user_chat_loop_context(
        **_base_builder_kwargs(),
        dual_llm_chat_msgs=chat_msgs,
        dual_llm_tool_msgs=tool_msgs,
        prompt_bundle=PromptBundle(
            identity="",
            soul="",
            user_md="",
            memory_md="",
        ),
        context_meta=ContextMeta(),
    )

    assert context.companion_turn_track == CompanionTurnTrack.USER_CHAT
    assert context.dual_llm_chat_msgs == chat_msgs
    assert context.dual_llm_tool_msgs == tool_msgs
    assert context.langsmith.foreground_source == SOURCE_FOREGROUND_DUAL_LLM_ENVELOPE
    assert context.prompt_plan is None


def test_resolved_user_turn_llm_loop_mode_defaults_to_dual_llm() -> None:
    assert resolved_user_turn_llm_loop_mode() == UserTurnLlmLoopMode.DUAL_LLM
