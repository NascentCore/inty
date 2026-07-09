"""Tests for interim greeting AgenticLoop context helpers (PR-2)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.companion_harness.companion.models import CompanionTurnTrack
from app.core.companion_harness.memory.memory_store_path_constants import (
    TRANSCRIPT_JSONL_REL,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.turn_tail_user import (
    TurnTailUserMessage,
)
from app.core.companion_harness.companion.langsmith_turn_slice import (
    CompanionTurnLangsmithSlice,
)
from app.core.companion_harness.loop.context import (
    build_implicit_sign_on_greeting_loop_context,
)
from app.core.companion_harness.prompting.track_composer import (
    TrackPromptComposer,
)
from tests.app.core.companion_harness.loop.context_builder_test_support import (
    loop_execution_for_track,
)
from app.core.agentic_companion.types import (
    UserMessageBatch,
    synthetic_user_message_batch,
)


def test_compose_from_openai_messages_wraps_dialogue() -> None:
    messages = [
        {"role": "system", "content": "You are Inty."},
        {"role": "user", "content": "hello"},
    ]
    plan = TrackPromptComposer().compose_from_openai_messages(messages, tools=())
    assert len(plan.messages) == 2
    assert plan.tools == ()
    assert plan.tool_choice is None


def test_synthetic_user_message_batch_correlates_agent_initiated_turn() -> None:
    batch = synthetic_user_message_batch(
        user_msg_uuid="uid-greet-1",
        track_label="implicit_sign_on_greeting",
    )
    assert (
        batch.batch_id
        == "agent-initiated:implicit_sign_on_greeting:uid-greet-1"
    )
    assert batch.message_ids == ("uid-greet-1",)


def test_build_implicit_sign_on_greeting_loop_context_sets_track() -> None:
    ts = datetime.now(UTC)
    batch = UserMessageBatch(
        batch_id="agent-initiated:greeting:u1", message_ids=("u1",)
    )
    tail = (
        TurnTailUserMessage(
            message_id="u1",
            text="[user signed on]",
            received_at_utc=ts,
        ),
    )
    plan = TrackPromptComposer().compose_from_openai_messages(
        [{"role": "system", "content": "greet"}],
        tools=(),
    )
    ctx = build_implicit_sign_on_greeting_loop_context(
        messages=[{"role": "system", "content": "greet"}],
        repository_only_store_text=False,
        trace_id="trace-1",
        user_text="",
        ts_user=ts,
        user_msg_uuid="u1",
        transcript_rel=TRANSCRIPT_JSONL_REL,
        langsmith_slice=CompanionTurnLangsmithSlice.app_default(),
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        ),
        stack_depth=1,
        langsmith_trace_id="",
        langsmith_run_id="",
        output_queue=object(),  # type: ignore[arg-type]
        user_message_batch=batch,
        tail_user_messages=tail,
        prompt_plan=plan,
        execution=loop_execution_for_track(
            track=CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING,
            user_text="",
            has_openai_tools=False,
        ),
    )
    assert (
        ctx.companion_turn_track == CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING
    )
    assert ctx.execution.max_tool_call_rounds == 0
    assert ctx.openai_tools == ()
