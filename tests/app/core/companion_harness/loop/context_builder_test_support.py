"""Shared test-only factories for ``loop/context.py`` builder unit tests.

Used by ``test_context.py`` and ``test_bootstrap_user_chat_loop_context.py``.
For legacy sidecar / ``LegacyAgenticLoopContext`` tests, see ``test_support.py``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.output_queue import OutputQueue
from app.core.companion_harness.agentic_companion.types import UserMessageBatch
from app.core.companion_harness.companion.langsmith_turn_slice import (
    CompanionTurnLangsmithSlice,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)


def runtime_context_for_builder_tests() -> TurnRuntimeContext:
    return TurnRuntimeContext(
        channel=CompanionRuntimeChannel.APP,
        implicit_signal_bundle=None,
    )


def langsmith_slice_for_builder_tests() -> CompanionTurnLangsmithSlice:
    return CompanionTurnLangsmithSlice.from_runtime_context(
        runtime_context_for_builder_tests()
    )


def output_queue_for_builder_tests() -> OutputQueue:
    return OutputQueue(scope=AgentScope(user_id="u1", agent_id="a1"))


def user_message_batch_for_builder_tests() -> UserMessageBatch:
    return UserMessageBatch(batch_id="batch-1", message_ids=("input-1",))


def base_user_chat_loop_builder_kwargs() -> dict:
    """Minimal kwargs shared by bootstrap and settled context builder tests."""
    return {
        "messages": [{"role": "user", "content": "hi"}],
        "tools_for_turn": [],
        "repository_only_store_text": False,
        "trace_id": "trace-1",
        "user_text": "hi",
        "ts_user": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "user_msg_uuid": "user-msg-1",
        "transcript_rel": "transcript.jsonl",
        "langsmith_slice": langsmith_slice_for_builder_tests(),
        "runtime_context": runtime_context_for_builder_tests(),
        "memory_bootstrap_type": "user_interactive",
        "stack_depth": 1,
        "langsmith_trace_id": "ls-1",
        "langsmith_run_id": "run-1",
        "output_queue": output_queue_for_builder_tests(),
        "user_message_batch": user_message_batch_for_builder_tests(),
    }
