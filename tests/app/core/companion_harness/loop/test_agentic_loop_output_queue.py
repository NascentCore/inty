"""Tests for production ``AgenticLoop`` direct user-turn OutputQueue delivery."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.output_queue import (
    OutputQueue,
    OutputQueueAppendInput,
    ReadyOutputMessage,
    clear_output_queues_for_tests,
)
from app.core.companion_harness.agentic_companion.types import UserMessageBatch
from app.core.companion_harness.companion.langsmith_turn_slice import (
    CompanionTurnLangsmithSlice,
)
from app.core.companion_harness.companion.models import (
    PROACTIVE_CHAT_SILENT_TOKEN,
    CompanionTurnTrack,
    InnerTickActivity,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.llm.langsmith_invocation_extra import (
    SOURCE_SINGLE_COMPLETION,
)
from app.core.companion_harness.loop.agentic_loop import (
    AgenticLoop,
    user_visible_assistant_text,
)
from app.core.companion_harness.loop.context import (
    AgenticLoopContext,
    AgenticLoopLangsmithContext,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.tools.companion_tool_definitions import (
    MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
)
from app.core.companion_harness.companion.turn_routes import BootstrapInterimOutput
from app.services.agentic_companion.downlink import DownlinkKind


def _bootstrap_interim(*, text: str) -> BootstrapInterimOutput:
    return BootstrapInterimOutput(
        text=text,
        user_msg_uuid="user-msg-1",
        trace_id="trace-1",
        langsmith_trace_id="ls-1",
        langsmith_run_id="run-1",
        round_index=1,
        had_tool_calls=False,
        assistant_msg_uuid="assistant-1",
    )


@pytest.fixture(autouse=True)
def _clear_registry() -> None:
    clear_output_queues_for_tests()
    yield
    clear_output_queues_for_tests()


def _runtime_context() -> TurnRuntimeContext:
    return TurnRuntimeContext(
        channel=CompanionRuntimeChannel.APP,
        implicit_signal_bundle=None,
    )


def _langsmith_slice() -> CompanionTurnLangsmithSlice:
    return CompanionTurnLangsmithSlice.from_runtime_context(_runtime_context())


def _loop_store() -> MemoryStore:
    store = MemoryStore(
        scope=CompanionScope("user-1", "agent-1", "chat-1"),
        repository=None,
    )
    store.write_document("transcript.jsonl", "")
    return store


def _assert_user_transcript_row(store: MemoryStore) -> None:
    transcript_lines = store.read_document("transcript.jsonl").splitlines()
    assert len(transcript_lines) == 1
    transcript_row = json.loads(transcript_lines[0])
    assert transcript_row["role"] == "user"
    assert transcript_row["content"] == "hi"
    assert transcript_row["uuid"] == "user-msg-1"


def _loop_context(*, output_queue: OutputQueue) -> AgenticLoopContext:
    batch = UserMessageBatch(batch_id="batch-1", message_ids=("input-1",))
    return AgenticLoopContext(
        openai_messages=({"role": "user", "content": "hi"},),
        openai_tools=(),
        write_allowlist=MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
        repository_only_store_text=False,
        trace_id="trace-1",
        user_text="hi",
        ts_user=datetime(2026, 1, 1, tzinfo=timezone.utc),
        user_msg_uuid="user-msg-1",
        transcript_rel="transcript.jsonl",
        langsmith=AgenticLoopLangsmithContext(
            turn_slice=_langsmith_slice(),
            foreground_source=SOURCE_SINGLE_COMPLETION,
            trace_id="",
            run_id="",
        ),
        inner_tick_turn=False,
        inner_tick_activity=InnerTickActivity.MAINTENANCE,
        runtime_context=_runtime_context(),
        max_tool_rounds=4,
        after_tool_messages_appended=None,
        high_reasoning=False,
        output_queue=output_queue,
        user_message_batch=batch,
        context_meta=None,
    )


def test_user_visible_assistant_text_filters_blank_and_silent() -> None:
    assert user_visible_assistant_text("") is None
    assert user_visible_assistant_text("   ") is None
    assert user_visible_assistant_text(PROACTIVE_CHAT_SILENT_TOKEN) is None
    assert user_visible_assistant_text("  [SILENT]  ") is None
    assert user_visible_assistant_text("hello") == "hello"
    assert user_visible_assistant_text("  hello  ") == "hello"


@pytest.mark.asyncio
async def test_agentic_loop_appends_each_non_empty_assistant_output() -> None:
    scope = AgentScope(user_id="u1", agent_id="a1")
    domain = OutputQueue(scope=scope)
    ready_a = ReadyOutputMessage(
        message_id="msg-a",
        batch_id="batch-1",
        kind=DownlinkKind.USER_REPLY,
        text="first",
        sequence=1,
        message_ids=("input-1",),
    )
    ready_b = ReadyOutputMessage(
        message_id="msg-b",
        batch_id="batch-1",
        kind=DownlinkKind.USER_REPLY,
        text="second",
        sequence=2,
        message_ids=("input-1",),
    )
    domain.append_user_reply = AsyncMock(side_effect=[ready_a, ready_b])  # type: ignore[method-assign]
    context = _loop_context(output_queue=domain)

    async def _fake_sync_loop(loop_input):  # type: ignore[no-untyped-def]
        await loop_input.interim_output_sink(
            _bootstrap_interim(text="first"),
        )
        await loop_input.interim_output_sink(
            BootstrapInterimOutput(
                text="second",
                user_msg_uuid="user-msg-1",
                trace_id="trace-1",
                langsmith_trace_id="ls-1",
                langsmith_run_id="run-1",
                round_index=2,
                had_tool_calls=False,
                assistant_msg_uuid="assistant-2",
            ),
        )
        from app.core.companion_harness.companion.in_turn_sync_tool_loop import (
            InTurnSyncToolLoopResult,
        )

        return InTurnSyncToolLoopResult(
            assistant_text="second",
            langsmith_trace_id="ls-1",
            langsmith_run_id="run-1",
            skip_final_transcript_assistant_row=True,
            last_interim_assistant_msg_uuid="assistant-1",
            loop_persisted_user_transcript=True,
        )

    with patch(
        "app.core.companion_harness.loop.agentic_loop.run_in_turn_sync_tool_loop",
        new=AsyncMock(side_effect=_fake_sync_loop),
    ):
        store = _loop_store()
        result = await AgenticLoop(
            store=store,
            llm_client=MagicMock(),
            legacy_llm_client=MagicMock(),
        ).run_single_llm_user_turn(context=context)

    assert result.output_message_ids == ("msg-a", "msg-b")
    append_inputs = [
        call.args[0] for call in domain.append_user_reply.await_args_list
    ]
    assert all(isinstance(item, OutputQueueAppendInput) for item in append_inputs)
    assert append_inputs[0].message_ids == ("input-1",)
    assert append_inputs[0].batch_id == "batch-1"
    _assert_user_transcript_row(store)


@pytest.mark.asyncio
async def test_agentic_loop_skips_empty_assistant_output() -> None:
    scope = AgentScope(user_id="u2", agent_id="a2")
    domain = MagicMock(spec=OutputQueue)
    domain.append_user_reply = AsyncMock()
    context = _loop_context(output_queue=domain)

    async def _fake_sync_loop(loop_input):  # type: ignore[no-untyped-def]
        await loop_input.interim_output_sink(
            _bootstrap_interim(text="   "),
        )
        from app.core.companion_harness.companion.in_turn_sync_tool_loop import (
            InTurnSyncToolLoopResult,
        )

        return InTurnSyncToolLoopResult(
            assistant_text="",
            langsmith_trace_id="",
            langsmith_run_id="",
            skip_final_transcript_assistant_row=False,
            last_interim_assistant_msg_uuid=None,
            loop_persisted_user_transcript=True,
        )

    with patch(
        "app.core.companion_harness.loop.agentic_loop.run_in_turn_sync_tool_loop",
        new=AsyncMock(side_effect=_fake_sync_loop),
    ):
        result = await AgenticLoop(
            store=_loop_store(),
            llm_client=MagicMock(),
            legacy_llm_client=MagicMock(),
        ).run_single_llm_user_turn(context=context)

    domain.append_user_reply.assert_not_awaited()
    assert result.output_message_ids == ()


@pytest.mark.asyncio
async def test_agentic_loop_skips_silent_assistant_output() -> None:
    scope = AgentScope(user_id="u2b", agent_id="a2b")
    domain = MagicMock(spec=OutputQueue)
    domain.append_user_reply = AsyncMock()
    context = _loop_context(output_queue=domain)

    async def _fake_sync_loop(loop_input):  # type: ignore[no-untyped-def]
        await loop_input.interim_output_sink(
            _bootstrap_interim(text=PROACTIVE_CHAT_SILENT_TOKEN),
        )
        from app.core.companion_harness.companion.in_turn_sync_tool_loop import (
            InTurnSyncToolLoopResult,
        )

        return InTurnSyncToolLoopResult(
            assistant_text=PROACTIVE_CHAT_SILENT_TOKEN,
            langsmith_trace_id="",
            langsmith_run_id="",
            skip_final_transcript_assistant_row=False,
            last_interim_assistant_msg_uuid=None,
            loop_persisted_user_transcript=True,
        )

    with patch(
        "app.core.companion_harness.loop.agentic_loop.run_in_turn_sync_tool_loop",
        new=AsyncMock(side_effect=_fake_sync_loop),
    ):
        result = await AgenticLoop(
            store=_loop_store(),
            llm_client=MagicMock(),
            legacy_llm_client=MagicMock(),
        ).run_single_llm_user_turn(context=context)

    domain.append_user_reply.assert_not_awaited()
    assert result.output_message_ids == ()


@pytest.mark.asyncio
async def test_agentic_loop_uses_prompt_plan_path_when_set() -> None:
    from app.core.companion_harness.prompt_builder import (
        PromptMessage,
        PromptMessageRole,
        PromptPlan,
    )

    scope = AgentScope(user_id="u3", agent_id="a3")
    domain = MagicMock(spec=OutputQueue)
    domain.append_user_reply = AsyncMock()
    context = _loop_context(output_queue=domain)
    prompt_plan = PromptPlan(
        messages=(
            PromptMessage(role=PromptMessageRole.SYSTEM, content="sys"),
            PromptMessage(role=PromptMessageRole.USER, content="hi"),
        ),
        tools=(),
        tool_choice=None,
    )
    context = replace(context, prompt_plan=prompt_plan)

    async def _fake_prompt_plan_loop(  # type: ignore[no-untyped-def]
        ctx,
        *,
        store,
        llm_client,
        interim_output_sink,
    ):
        assert ctx.prompt_plan is prompt_plan
        from app.core.companion_harness.companion.in_turn_sync_tool_loop import (
            InTurnSyncToolLoopResult,
        )

        return InTurnSyncToolLoopResult(
            assistant_text="done",
            langsmith_trace_id="",
            langsmith_run_id="",
            skip_final_transcript_assistant_row=True,
            last_interim_assistant_msg_uuid=None,
            loop_persisted_user_transcript=True,
        )

    with patch(
        "app.core.companion_harness.loop.agentic_loop.run_in_turn_sync_tool_loop",
        new=AsyncMock(),
    ) as legacy_mock, patch(
        "app.core.companion_harness.loop.agentic_loop._run_prompt_plan_tool_loop",
        new=AsyncMock(side_effect=_fake_prompt_plan_loop),
    ) as prompt_plan_mock:
        result = await AgenticLoop(
            store=_loop_store(),
            llm_client=MagicMock(),
            legacy_llm_client=MagicMock(),
        ).run_single_llm_user_turn(context=context)

    prompt_plan_mock.assert_awaited_once()
    legacy_mock.assert_not_awaited()
    assert result.assistant_text == "done"


@pytest.mark.asyncio
async def test_prompt_plan_tool_loop_continuation_uses_async_chat_completion() -> None:
    from app.core.companion_harness.loop.agentic_loop import (
        _run_prompt_plan_tool_loop,
    )
    from app.core.companion_harness.prompt_builder import (
        PromptMessage,
        PromptMessageRole,
        PromptPlan,
    )

    def _response(text: str):  # type: ignore[no-untyped-def]
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=text, tool_calls=[]),
                )
            ]
        )

    domain = MagicMock(spec=OutputQueue)
    context = _loop_context(output_queue=domain)
    prompt_plan = PromptPlan(
        messages=(
            PromptMessage(role=PromptMessageRole.SYSTEM, content="sys"),
            PromptMessage(role=PromptMessageRole.USER, content="hi"),
        ),
        tools=({"type": "function", "function": {"name": "generate_image"}},),
        tool_choice=None,
    )
    llm_client = MagicMock()
    llm_client.resolve_model.return_value = SimpleNamespace(
        id_on_provider="test/model"
    )
    llm_client.chat_completion = AsyncMock(
        side_effect=[_response("initial"), _response("final")]
    )
    context = replace(context, prompt_plan=prompt_plan, high_reasoning=True)

    async def _fake_resolver(  # type: ignore[no-untyped-def]
        *,
        response,
        openai_messages,
        max_tool_call_rounds,
        execute_tool_call,
        continue_chat,
        build_assistant_tool_call_message,
        insert_system_message,
        initial_trace_id,
        after_tool_messages_appended,
        on_assistant_message,
    ):
        assert openai_messages == [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
        ]
        next_resp, _trace_id = await continue_chat(openai_messages)
        return SimpleNamespace(
            trace_id="trace-next",
            response=next_resp,
            messages=openai_messages,
        )

    store = _loop_store()
    with patch(
        "app.core.companion_harness.loop.agentic_loop.resolve_openai_tool_call_loop_async",
        new=AsyncMock(side_effect=_fake_resolver),
    ):
        result = await _run_prompt_plan_tool_loop(
            context,
            store=store,
            llm_client=llm_client,
            interim_output_sink=None,
        )

    assert llm_client.chat_completion.await_count == 2
    initial_call = llm_client.chat_completion.await_args_list[0]
    assert initial_call.kwargs["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
    ]
    assert initial_call.kwargs["tools"] == list(prompt_plan.tools)
    assert initial_call.kwargs["tool_choice"] is None
    assert initial_call.kwargs["high_reasoning"] is True
    continuation_call = llm_client.chat_completion.await_args_list[1]
    expected_extra = _langsmith_slice().foreground_invocation_extra(
        source=SOURCE_SINGLE_COMPLETION,
        extra_metadata=None,
    )
    assert initial_call.kwargs["langsmith_extra"] == expected_extra
    assert continuation_call.kwargs["langsmith_extra"] == expected_extra
    assert result.assistant_text == "final"


@pytest.mark.asyncio
async def test_dual_llm_user_turn_appends_foreground_and_tool_leg() -> None:
    from app.core.companion_harness.companion.dual_llm_foreground_chat import (
        DualLlmForegroundChatResult,
    )
    from app.core.companion_harness.companion.models import ContextMeta
    from app.core.companion_harness.prompting.bundle import PromptBundle
    from app.core.companion_harness.tools.tool_background import ToolOutputEvent

    scope = AgentScope(user_id="u4", agent_id="a4")
    domain = OutputQueue(scope=scope)
    ready_fg = ReadyOutputMessage(
        message_id="msg-fg",
        batch_id="batch-1",
        kind=DownlinkKind.USER_REPLY,
        text="foreground",
        sequence=1,
        message_ids=("input-1",),
    )
    ready_tool = ReadyOutputMessage(
        message_id="msg-tool",
        batch_id="batch-1",
        kind=DownlinkKind.USER_REPLY,
        text="tool reply",
        sequence=2,
        message_ids=("input-1",),
    )
    domain.append_user_reply = AsyncMock(side_effect=[ready_fg, ready_tool])  # type: ignore[method-assign]
    batch = UserMessageBatch(batch_id="batch-1", message_ids=("input-1",))
    context = AgenticLoopContext(
        openai_messages=({"role": "user", "content": "hi"},),
        openai_tools=(),
        write_allowlist=MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
        repository_only_store_text=False,
        trace_id="trace-1",
        user_text="hi",
        ts_user=datetime(2026, 1, 1, tzinfo=timezone.utc),
        user_msg_uuid="user-msg-1",
        transcript_rel="transcript.jsonl",
        langsmith=AgenticLoopLangsmithContext(
            turn_slice=_langsmith_slice(),
            foreground_source="foreground_dual_llm_envelope",
            trace_id="",
            run_id="",
        ),
        inner_tick_turn=False,
        inner_tick_activity=InnerTickActivity.MAINTENANCE,
        runtime_context=_runtime_context(),
        max_tool_rounds=4,
        after_tool_messages_appended=None,
        high_reasoning=False,
        output_queue=domain,
        user_message_batch=batch,
        companion_turn_track=CompanionTurnTrack.USER_CHAT,
        dual_llm_chat_msgs=({"role": "user", "content": "hi"},),
        dual_llm_tool_msgs=({"role": "user", "content": "hi"},),
        prompt_bundle=PromptBundle(
            identity="",
            soul="",
            user_md="",
            memory_md="",
        ),
        context_meta=ContextMeta(),
    )

    fg_result = DualLlmForegroundChatResult(
        assistant_text="foreground",
        significance_meta=None,
        turn_recall="recall-1",
        langsmith_trace_id="ls-fg",
        langsmith_run_id="run-fg",
        tool_msgs_for_bg=({"role": "user", "content": "hi"},),
        force_tools_first_round=False,
    )

    async def _fake_tool_loop(**kwargs):  # type: ignore[no-untyped-def]
        kwargs["on_event"](
            ToolOutputEvent(
                scope_registry_key="k",
                memory_store=_loop_store(),
                user_msg_uuid="user-msg-1",
                assistant_msg_uuid="assistant-1",
                text="tool reply",
                ts="",
                elapsed_ms=0,
                output_to_user=True,
            )
        )

    store = _loop_store()
    with patch(
        "app.core.companion_harness.loop.agentic_loop.run_dual_llm_foreground_chat",
        new=AsyncMock(return_value=fg_result),
    ), patch(
        "app.core.companion_harness.loop.agentic_loop.run_tool_background_loop",
        new=AsyncMock(side_effect=_fake_tool_loop),
    ):
        result = await AgenticLoop(
            store=store,
            llm_client=MagicMock(),
            legacy_llm_client=MagicMock(),
        ).run_dual_llm_user_turn(context=context)

    assert result.output_message_ids == ("msg-fg", "msg-tool")
    assert result.tool_background_started is False
    assert result.turn_recall == "recall-1"
    _assert_user_transcript_row(store)


@pytest.mark.asyncio
async def test_dual_llm_user_turn_skips_output_to_user_false() -> None:
    from app.core.companion_harness.companion.dual_llm_foreground_chat import (
        DualLlmForegroundChatResult,
    )
    from app.core.companion_harness.companion.models import ContextMeta
    from app.core.companion_harness.prompting.bundle import PromptBundle
    from app.core.companion_harness.tools.tool_background import ToolOutputEvent

    scope = AgentScope(user_id="u5", agent_id="a5")
    domain = MagicMock(spec=OutputQueue)
    domain.append_user_reply = AsyncMock()
    batch = UserMessageBatch(batch_id="batch-1", message_ids=("input-1",))
    context = AgenticLoopContext(
        openai_messages=({"role": "user", "content": "hi"},),
        openai_tools=(),
        write_allowlist=MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
        repository_only_store_text=False,
        trace_id="trace-1",
        user_text="hi",
        ts_user=datetime(2026, 1, 1, tzinfo=timezone.utc),
        user_msg_uuid="user-msg-1",
        transcript_rel="transcript.jsonl",
        langsmith=AgenticLoopLangsmithContext(
            turn_slice=_langsmith_slice(),
            foreground_source="foreground_dual_llm_envelope",
            trace_id="",
            run_id="",
        ),
        inner_tick_turn=False,
        inner_tick_activity=InnerTickActivity.MAINTENANCE,
        runtime_context=_runtime_context(),
        max_tool_rounds=4,
        after_tool_messages_appended=None,
        high_reasoning=False,
        output_queue=domain,
        user_message_batch=batch,
        companion_turn_track=CompanionTurnTrack.USER_CHAT,
        dual_llm_chat_msgs=({"role": "user", "content": "hi"},),
        dual_llm_tool_msgs=({"role": "user", "content": "hi"},),
        prompt_bundle=PromptBundle(
            identity="",
            soul="",
            user_md="",
            memory_md="",
        ),
        context_meta=ContextMeta(),
    )
    fg_result = DualLlmForegroundChatResult(
        assistant_text="",
        significance_meta=None,
        turn_recall=None,
        langsmith_trace_id="",
        langsmith_run_id="",
        tool_msgs_for_bg=({"role": "user", "content": "hi"},),
        force_tools_first_round=False,
    )

    async def _fake_tool_loop(**kwargs):  # type: ignore[no-untyped-def]
        kwargs["on_event"](
            ToolOutputEvent(
                scope_registry_key="k",
                memory_store=_loop_store(),
                user_msg_uuid="user-msg-1",
                assistant_msg_uuid="assistant-1",
                text="silent recap",
                ts="",
                elapsed_ms=0,
                output_to_user=False,
            )
        )

    with patch(
        "app.core.companion_harness.loop.agentic_loop.run_dual_llm_foreground_chat",
        new=AsyncMock(return_value=fg_result),
    ), patch(
        "app.core.companion_harness.loop.agentic_loop.run_tool_background_loop",
        new=AsyncMock(side_effect=_fake_tool_loop),
    ):
        result = await AgenticLoop(
            store=_loop_store(),
            llm_client=MagicMock(),
            legacy_llm_client=MagicMock(),
        ).run_dual_llm_user_turn(context=context)

    domain.append_user_reply.assert_not_awaited()
    assert result.output_message_ids == ()


@pytest.mark.asyncio
async def test_dual_llm_user_turn_skips_silent_foreground_output() -> None:
    from app.core.companion_harness.companion.dual_llm_foreground_chat import (
        DualLlmForegroundChatResult,
    )
    from app.core.companion_harness.companion.models import ContextMeta
    from app.core.companion_harness.prompting.bundle import PromptBundle

    domain = MagicMock(spec=OutputQueue)
    domain.append_user_reply = AsyncMock()
    batch = UserMessageBatch(batch_id="batch-1", message_ids=("input-1",))
    context = AgenticLoopContext(
        openai_messages=({"role": "user", "content": "hi"},),
        openai_tools=(),
        write_allowlist=MEMORY_STORE_WRITE_DOCUMENT_ALLOWLIST,
        repository_only_store_text=False,
        trace_id="trace-1",
        user_text="hi",
        ts_user=datetime(2026, 1, 1, tzinfo=timezone.utc),
        user_msg_uuid="user-msg-1",
        transcript_rel="transcript.jsonl",
        langsmith=AgenticLoopLangsmithContext(
            turn_slice=_langsmith_slice(),
            foreground_source="foreground_dual_llm_envelope",
            trace_id="",
            run_id="",
        ),
        inner_tick_turn=True,
        inner_tick_activity=InnerTickActivity.PROACTIVE_CHAT,
        runtime_context=_runtime_context(),
        max_tool_rounds=4,
        after_tool_messages_appended=None,
        high_reasoning=False,
        output_queue=domain,
        user_message_batch=batch,
        companion_turn_track=CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT,
        dual_llm_chat_msgs=({"role": "user", "content": "hi"},),
        dual_llm_tool_msgs=({"role": "user", "content": "hi"},),
        prompt_bundle=PromptBundle(
            identity="",
            soul="",
            user_md="",
            memory_md="",
        ),
        context_meta=ContextMeta(),
    )
    fg_result = DualLlmForegroundChatResult(
        assistant_text=PROACTIVE_CHAT_SILENT_TOKEN,
        significance_meta=None,
        turn_recall=None,
        langsmith_trace_id="",
        langsmith_run_id="",
        tool_msgs_for_bg=({"role": "user", "content": "hi"},),
        force_tools_first_round=False,
    )

    with patch(
        "app.core.companion_harness.loop.agentic_loop.run_dual_llm_foreground_chat",
        new=AsyncMock(return_value=fg_result),
    ), patch(
        "app.core.companion_harness.loop.agentic_loop.run_tool_background_loop",
        new=AsyncMock(),
    ):
        result = await AgenticLoop(
            store=_loop_store(),
            llm_client=MagicMock(),
            legacy_llm_client=MagicMock(),
        ).run_dual_llm_user_turn(context=context)

    domain.append_user_reply.assert_not_awaited()
    assert result.output_message_ids == ()

