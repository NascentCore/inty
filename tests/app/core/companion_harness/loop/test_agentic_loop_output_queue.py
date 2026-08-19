"""Tests for production ``AgenticLoop`` direct user-turn OutputQueue delivery."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.agentic_companion.output_queue import (
    OutputQueue,
    OutputQueueAppendInput,
    ReadyOutputMessage,
    clear_output_queues_for_tests,
)
from app.core.agentic_companion.types import UserMessageBatch
from app.core.companion_harness.companion.langsmith_turn_slice import (
    CompanionTurnLangsmithSlice,
)
from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.llm.langsmith_invocation_extra import (
    LangsmithLlmSource,
)
from tests.app.core.companion_harness.loop.context_builder_test_support import (
    loop_execution_for_track,
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
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)
from app.core.companion_harness.companion.turn_routes import (
    InTurnInterimOutput,
)
from app.core.companion_harness.companion.turn_tail_user import (
    TurnTailUserMessage,
)
from app.core.companion_harness.loop.runtime_system_clauses import (
    REPLY_IN_USER_LANGUAGE_CLAUSE,
)
from app.core.companion_harness.prompt_builder import (
    PromptMessage,
    PromptMessageRole,
    PromptPlan,
)
from app.core.agentic_companion.types import OutputMessageKind


def _in_turn_interim(*, text: str) -> InTurnInterimOutput:
    return InTurnInterimOutput(
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
        channel=ChannelKind.APP_WS,
        implicit_signal_bundle=None,
    )


def _langsmith_slice() -> CompanionTurnLangsmithSlice:
    return CompanionTurnLangsmithSlice.from_runtime_context(_runtime_context())


def _loop_store() -> MemoryStore:
    store = MemoryStore(
        scope=CompanionScope("user-1", "agent-1", "chat-1"),
        repository=None,
    )
    store.write_document(DEFAULT_MEMORY_STORE_SCOPE_PATHS.transcript, "")
    return store


def _assert_user_transcript_row(store: MemoryStore) -> None:
    transcript_lines = store.read_document(
        DEFAULT_MEMORY_STORE_SCOPE_PATHS.transcript
    ).splitlines()
    assert len(transcript_lines) == 1
    transcript_row = json.loads(transcript_lines[0])
    assert transcript_row["role"] == "user"
    assert transcript_row["content"] == "hi"
    assert transcript_row["uuid"] == "user-msg-1"


def _tail() -> tuple[TurnTailUserMessage, ...]:
    return (
        TurnTailUserMessage(
            message_id="user-msg-1",
            text="hi",
            received_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
        ),
    )


def _default_prompt_plan() -> PromptPlan:
    return PromptPlan(
        messages=(
            PromptMessage(role=PromptMessageRole.SYSTEM, content="sys"),
            PromptMessage(role=PromptMessageRole.USER, content="hi"),
        ),
        tools=(),
        tool_choice=None,
    )


def _loop_context(
    *,
    output_queue: OutputQueue,
    with_in_turn_tools: bool = False,
) -> AgenticLoopContext:
    openai_tools: tuple[dict[str, Any], ...] = ()
    if with_in_turn_tools:
        openai_tools = ({"type": "function", "function": {"name": "noop"}},)
    batch = UserMessageBatch(batch_id="batch-1", message_ids=("input-1",))
    return AgenticLoopContext(
        openai_messages=({"role": "user", "content": "hi"},),
        openai_tools=openai_tools,
        companion_turn_track=CompanionTurnTrack.USER_CHAT,
        execution=loop_execution_for_track(
            track=CompanionTurnTrack.USER_CHAT,
            user_text="hi",
            has_openai_tools=with_in_turn_tools,
        ),
        repository_only_store_text=False,
        trace_id="trace-1",
        user_text="hi",
        ts_user=datetime(2026, 1, 1, tzinfo=UTC),
        user_msg_uuid="user-msg-1",
        tail_user_messages=_tail(),
        transcript_rel=DEFAULT_MEMORY_STORE_SCOPE_PATHS.transcript,
        langsmith=AgenticLoopLangsmithContext(
            turn_slice=_langsmith_slice(),
            trace_id="",
            run_id="",
        ),
        runtime_context=_runtime_context(),
        after_tool_messages_appended=None,
        output_queue=output_queue,
        user_message_batch=batch,
        context_meta=None,
        prompt_plan=_default_prompt_plan(),
    )


def _dual_llm_loop_context(
    *,
    output_queue: OutputQueue,
    companion_turn_track: CompanionTurnTrack,
) -> AgenticLoopContext:
    from app.core.companion_harness.companion.models import ContextMeta
    from app.core.companion_harness.prompting.bundle import PromptBundle

    batch = UserMessageBatch(batch_id="batch-1", message_ids=("input-1",))
    return AgenticLoopContext(
        openai_messages=({"role": "user", "content": "hi"},),
        openai_tools=(),
        companion_turn_track=companion_turn_track,
        execution=loop_execution_for_track(
            track=companion_turn_track,
            user_text="hi",
            has_openai_tools=False,
        ),
        repository_only_store_text=False,
        trace_id="trace-1",
        user_text="hi",
        ts_user=datetime(2026, 1, 1, tzinfo=UTC),
        user_msg_uuid="user-msg-1",
        tail_user_messages=_tail(),
        transcript_rel=DEFAULT_MEMORY_STORE_SCOPE_PATHS.transcript,
        langsmith=AgenticLoopLangsmithContext(
            turn_slice=_langsmith_slice(),
            trace_id="",
            run_id="",
        ),
        runtime_context=_runtime_context(),
        after_tool_messages_appended=None,
        output_queue=output_queue,
        user_message_batch=batch,
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


def test_user_visible_assistant_text_filters_blank() -> None:
    assert user_visible_assistant_text("") is None
    assert user_visible_assistant_text("   ") is None
    assert user_visible_assistant_text("hello") == "hello"
    assert user_visible_assistant_text("  hello  ") == "hello"


@pytest.mark.asyncio
async def test_agentic_loop_appends_each_non_empty_assistant_output() -> None:
    scope = AgentScope(user_id="u1", agent_id="a1")
    domain = OutputQueue(scope=scope)
    ready_a = ReadyOutputMessage(
        message_id="msg-a",
        batch_id="batch-1",
        kind=OutputMessageKind.USER_REPLY,
        text="first",
        sequence=1,
        message_ids=("input-1",),
    )
    ready_b = ReadyOutputMessage(
        message_id="msg-b",
        batch_id="batch-1",
        kind=OutputMessageKind.USER_REPLY,
        text="second",
        sequence=2,
        message_ids=("input-1",),
    )
    domain.append_visible_message = AsyncMock(side_effect=[ready_a, ready_b])  # type: ignore[method-assign]
    context = _loop_context(output_queue=domain, with_in_turn_tools=True)

    async def _fake_prompt_plan_loop(  # type: ignore[no-untyped-def]
        ctx,
        *,
        store,
        llm_client,
        interim_output_sink,
        max_tool_call_rounds,
    ):
        await interim_output_sink(
            _in_turn_interim(text="first"),
        )
        await interim_output_sink(
            InTurnInterimOutput(
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
        "app.core.companion_harness.loop.agentic_loop._run_prompt_plan_tool_loop",
        new=AsyncMock(side_effect=_fake_prompt_plan_loop),
    ):
        store = _loop_store()
        result = await AgenticLoop(
            store=store,
            llm_client=MagicMock(),
            legacy_llm_client=MagicMock(),
        ).run_single_llm_turn(context=context)

    assert result.output_message_ids == ("msg-a", "msg-b")
    append_inputs = [
        call.args[0] for call in domain.append_visible_message.await_args_list
    ]
    assert all(
        isinstance(item, OutputQueueAppendInput) for item in append_inputs
    )
    assert append_inputs[0].message_ids == ("input-1",)
    assert append_inputs[0].kind == OutputMessageKind.USER_REPLY
    assert append_inputs[0].batch_id == "batch-1"
    _assert_user_transcript_row(store)


@pytest.mark.asyncio
async def test_agentic_loop_skips_empty_assistant_output() -> None:
    domain = MagicMock(spec=OutputQueue)
    domain.append_visible_message = AsyncMock()
    context = _loop_context(output_queue=domain, with_in_turn_tools=True)

    async def _fake_prompt_plan_loop(  # type: ignore[no-untyped-def]
        ctx,
        *,
        store,
        llm_client,
        interim_output_sink,
        max_tool_call_rounds,
    ):
        await interim_output_sink(
            _in_turn_interim(text="   "),
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
        "app.core.companion_harness.loop.agentic_loop._run_prompt_plan_tool_loop",
        new=AsyncMock(side_effect=_fake_prompt_plan_loop),
    ):
        result = await AgenticLoop(
            store=_loop_store(),
            llm_client=MagicMock(),
            legacy_llm_client=MagicMock(),
        ).run_single_llm_turn(context=context)

    domain.append_visible_message.assert_not_awaited()
    assert result.output_message_ids == ()


@pytest.mark.asyncio
async def test_agentic_loop_skips_silent_assistant_output() -> None:
    domain = MagicMock(spec=OutputQueue)
    domain.append_visible_message = AsyncMock()
    context = _loop_context(output_queue=domain, with_in_turn_tools=True)

    async def _fake_prompt_plan_loop(  # type: ignore[no-untyped-def]
        ctx,
        *,
        store,
        llm_client,
        interim_output_sink,
        max_tool_call_rounds,
    ):
        await interim_output_sink(
            _in_turn_interim(text=""),
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
        "app.core.companion_harness.loop.agentic_loop._run_prompt_plan_tool_loop",
        new=AsyncMock(side_effect=_fake_prompt_plan_loop),
    ):
        result = await AgenticLoop(
            store=_loop_store(),
            llm_client=MagicMock(),
            legacy_llm_client=MagicMock(),
        ).run_single_llm_turn(context=context)

    domain.append_visible_message.assert_not_awaited()
    assert result.output_message_ids == ()


@pytest.mark.asyncio
async def test_agentic_loop_uses_prompt_plan_path_when_set() -> None:
    from app.core.companion_harness.prompt_builder import (
        PromptMessage,
        PromptMessageRole,
        PromptPlan,
    )

    domain = MagicMock(spec=OutputQueue)
    domain.append_visible_message = AsyncMock()
    context = _loop_context(output_queue=domain, with_in_turn_tools=True)
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
        max_tool_call_rounds,
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
        "app.core.companion_harness.loop.agentic_loop._run_prompt_plan_tool_loop",
        new=AsyncMock(side_effect=_fake_prompt_plan_loop),
    ) as prompt_plan_mock:
        result = await AgenticLoop(
            store=_loop_store(),
            llm_client=MagicMock(),
            legacy_llm_client=MagicMock(),
        ).run_single_llm_turn(context=context)

    prompt_plan_mock.assert_awaited_once()
    assert result.assistant_text == "done"


@pytest.mark.asyncio
async def test_prompt_plan_tool_loop_continuation_uses_async_chat_completion() -> (
    None
):
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
    context = _loop_context(output_queue=domain, with_in_turn_tools=True)
    prompt_plan = PromptPlan(
        messages=(
            PromptMessage(role=PromptMessageRole.SYSTEM, content="sys"),
            PromptMessage(role=PromptMessageRole.USER, content="hi"),
        ),
        tools=({"type": "function", "function": {"name": "generate_image"}},),
        tool_choice=None,
    )
    refreshed_tools = (
        {
            "type": "function",
            "function": {"name": "memory_store_read_document"},
        },
    )

    async def _refresh_after_tool_round(
        messages_with_tool_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        messages_with_tool_results[0] = {
            "role": "system",
            "content": "refreshed sys",
        }
        return list(refreshed_tools)

    llm_client = MagicMock()
    llm_client.resolve_model.return_value = SimpleNamespace(
        id_on_provider="test/model"
    )
    llm_client.chat_completion = AsyncMock(
        side_effect=[_response("initial"), _response("final")]
    )
    context = replace(context, prompt_plan=prompt_plan)

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
            {"role": "system", "content": REPLY_IN_USER_LANGUAGE_CLAUSE},
            {"role": "user", "content": "hi"},
        ]
        await after_tool_messages_appended(openai_messages)
        assert openai_messages[0] == {
            "role": "system",
            "content": "refreshed sys",
        }
        next_resp, _trace_id = await continue_chat(openai_messages)
        return SimpleNamespace(
            trace_id="trace-next",
            response=next_resp,
            messages=openai_messages,
        )

    store = _loop_store()
    context = replace(
        context,
        after_tool_messages_appended=_refresh_after_tool_round,
    )
    with patch(
        "app.core.companion_harness.loop.agentic_loop.resolve_openai_tool_call_loop_async",
        new=AsyncMock(side_effect=_fake_resolver),
    ):
        result = await _run_prompt_plan_tool_loop(
            context,
            store=store,
            llm_client=llm_client,
            interim_output_sink=None,
            max_tool_call_rounds=context.execution.max_tool_call_rounds,
        )

    assert llm_client.chat_completion.await_count == 2
    initial_call = llm_client.chat_completion.await_args_list[0]
    assert initial_call.kwargs["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "system", "content": REPLY_IN_USER_LANGUAGE_CLAUSE},
        {"role": "user", "content": "hi"},
    ]
    assert initial_call.kwargs["tools"] == list(prompt_plan.tools)
    assert initial_call.kwargs["tool_choice"] is None
    assert initial_call.kwargs["high_reasoning"] is False
    continuation_call = llm_client.chat_completion.await_args_list[1]
    assert continuation_call.kwargs["tools"] == list(refreshed_tools)
    expected_extra = _langsmith_slice().foreground_invocation_extra(
        source=LangsmithLlmSource.SINGLE_COMPLETION.value,
        extra_metadata=None,
    )
    assert initial_call.kwargs["langsmith_extra"] == expected_extra
    assert continuation_call.kwargs["langsmith_extra"] == expected_extra
    assert result.assistant_text == "final"


@pytest.mark.asyncio
async def test_prompt_plan_tool_loop_injects_reply_language_clause() -> None:
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
    context = _loop_context(output_queue=domain, with_in_turn_tools=True)
    prompt_plan = PromptPlan(
        messages=(
            PromptMessage(role=PromptMessageRole.SYSTEM, content="sys"),
            PromptMessage(role=PromptMessageRole.USER, content="hello"),
        ),
        tools=(),
        tool_choice=None,
    )
    context = replace(context, prompt_plan=prompt_plan, user_text="hello")
    llm_client = MagicMock()
    llm_client.resolve_model.return_value = SimpleNamespace(
        id_on_provider="test/model"
    )
    llm_client.chat_completion = AsyncMock(return_value=_response("ok"))

    with patch(
        "app.core.companion_harness.loop.agentic_loop.resolve_openai_tool_call_loop_async",
        new=AsyncMock(
            return_value=SimpleNamespace(
                trace_id="trace-1",
                response=_response("ok"),
                messages=[],
            )
        ),
    ):
        await _run_prompt_plan_tool_loop(
            context,
            store=_loop_store(),
            llm_client=llm_client,
            interim_output_sink=None,
            max_tool_call_rounds=0,
        )

    initial_messages = llm_client.chat_completion.await_args_list[0].kwargs[
        "messages"
    ]
    assert initial_messages[1]["content"] == REPLY_IN_USER_LANGUAGE_CLAUSE
    assert initial_messages[2]["content"] == "hello"


@pytest.mark.asyncio
async def test_prompt_plan_tool_loop_skips_runtime_clause_when_fixed_language_configured(
    monkeypatch,
) -> None:
    from app.core.companion_harness.loop.agentic_loop import (
        _run_prompt_plan_tool_loop,
    )
    from app.core.companion_harness.loop.runtime_system_clauses import (
        fixed_reply_language_clause,
    )
    from app.core.companion_harness.prompt_builder import (
        PromptMessage,
        PromptMessageRole,
        PromptPlan,
    )

    monkeypatch.setattr(
        "app.core.companion_harness.loop.runtime_system_clauses.resolved_companion_harness_reply_language",
        lambda: "English",
    )

    def _response(text: str):  # type: ignore[no-untyped-def]
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=text, tool_calls=[]),
                )
            ]
        )

    fixed_clause = fixed_reply_language_clause(language="English")
    context = _loop_context(output_queue=MagicMock(spec=OutputQueue))
    prompt_plan = PromptPlan(
        messages=(
            PromptMessage(role=PromptMessageRole.SYSTEM, content="sys"),
            PromptMessage(
                role=PromptMessageRole.SYSTEM,
                content=fixed_clause,
            ),
            PromptMessage(role=PromptMessageRole.USER, content="hello"),
        ),
        tools=(),
        tool_choice=None,
    )
    context = replace(context, prompt_plan=prompt_plan, user_text="hello")
    llm_client = MagicMock()
    llm_client.resolve_model.return_value = SimpleNamespace(
        id_on_provider="test/model"
    )
    llm_client.chat_completion = AsyncMock(return_value=_response("ok"))

    with patch(
        "app.core.companion_harness.loop.agentic_loop.resolve_openai_tool_call_loop_async",
        new=AsyncMock(
            return_value=SimpleNamespace(
                trace_id="trace-1",
                response=_response("ok"),
                messages=[],
            )
        ),
    ):
        await _run_prompt_plan_tool_loop(
            context,
            store=_loop_store(),
            llm_client=llm_client,
            interim_output_sink=None,
            max_tool_call_rounds=0,
        )

    initial_messages = llm_client.chat_completion.await_args_list[0].kwargs[
        "messages"
    ]
    assert initial_messages == [
        {"role": "system", "content": "sys"},
        {"role": "system", "content": fixed_clause},
        {"role": "user", "content": "hello"},
    ]


@pytest.mark.asyncio
async def test_dual_llm_user_turn_injects_reply_language_clause() -> None:
    from app.core.companion_harness.companion.dual_llm_foreground_chat import (
        DualLlmForegroundChatResult,
    )

    domain = MagicMock(spec=OutputQueue)
    domain.append_visible_message = AsyncMock()
    context = _dual_llm_loop_context(
        output_queue=domain,
        companion_turn_track=CompanionTurnTrack.USER_CHAT,
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
    foreground_mock = AsyncMock(return_value=fg_result)

    with (
        patch(
            "app.core.companion_harness.loop.agentic_loop.run_dual_llm_foreground_chat",
            new=foreground_mock,
        ),
        patch(
            "app.core.companion_harness.loop.agentic_loop.run_tool_background_loop",
            new=AsyncMock(),
        ),
    ):
        await AgenticLoop(
            store=_loop_store(),
            llm_client=MagicMock(),
            legacy_llm_client=MagicMock(),
        ).run_dual_llm_turn(context=context)

    fg_input = foreground_mock.await_args.args[0]
    assert fg_input.chat_msgs[0]["content"] == REPLY_IN_USER_LANGUAGE_CLAUSE
    assert fg_input.chat_msgs[1]["content"] == "hi"
    assert fg_input.tool_msgs[0]["content"] == "hi"


@pytest.mark.asyncio
async def test_dual_llm_user_turn_appends_foreground_and_tool_leg() -> None:
    from app.core.companion_harness.companion.dual_llm_foreground_chat import (
        DualLlmForegroundChatResult,
    )
    from app.core.companion_harness.tools.tool_background import ToolOutputEvent

    scope = AgentScope(user_id="u4", agent_id="a4")
    domain = OutputQueue(scope=scope)
    ready_fg = ReadyOutputMessage(
        message_id="msg-fg",
        batch_id="batch-1",
        kind=OutputMessageKind.USER_REPLY,
        text="foreground",
        sequence=1,
        message_ids=("input-1",),
    )
    ready_tool = ReadyOutputMessage(
        message_id="msg-tool",
        batch_id="batch-1",
        kind=OutputMessageKind.TOOL_BACKGROUND,
        text="tool reply",
        sequence=2,
        message_ids=("input-1",),
    )
    domain.append_visible_message = AsyncMock(side_effect=[ready_fg, ready_tool])  # type: ignore[method-assign]
    context = _dual_llm_loop_context(
        output_queue=domain,
        companion_turn_track=CompanionTurnTrack.USER_CHAT,
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
    with (
        patch(
            "app.core.companion_harness.loop.agentic_loop.run_dual_llm_foreground_chat",
            new=AsyncMock(return_value=fg_result),
        ),
        patch(
            "app.core.companion_harness.loop.agentic_loop.run_tool_background_loop",
            new=AsyncMock(side_effect=_fake_tool_loop),
        ),
    ):
        result = await AgenticLoop(
            store=store,
            llm_client=MagicMock(),
            legacy_llm_client=MagicMock(),
        ).run_dual_llm_turn(context=context)

    assert result.output_message_ids == ("msg-fg", "msg-tool")
    assert result.tool_background_started is True
    assert result.turn_recall == "recall-1"
    append_inputs = [
        call.args[0] for call in domain.append_visible_message.await_args_list
    ]
    assert append_inputs[0].kind == OutputMessageKind.USER_REPLY
    assert append_inputs[1].kind == OutputMessageKind.TOOL_BACKGROUND
    _assert_user_transcript_row(store)


@pytest.mark.asyncio
async def test_dual_llm_user_turn_skips_output_to_user_false() -> None:
    from app.core.companion_harness.companion.dual_llm_foreground_chat import (
        DualLlmForegroundChatResult,
    )
    from app.core.companion_harness.tools.tool_background import ToolOutputEvent

    domain = MagicMock(spec=OutputQueue)
    domain.append_visible_message = AsyncMock()
    context = _dual_llm_loop_context(
        output_queue=domain,
        companion_turn_track=CompanionTurnTrack.USER_CHAT,
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

    with (
        patch(
            "app.core.companion_harness.loop.agentic_loop.run_dual_llm_foreground_chat",
            new=AsyncMock(return_value=fg_result),
        ),
        patch(
            "app.core.companion_harness.loop.agentic_loop.run_tool_background_loop",
            new=AsyncMock(side_effect=_fake_tool_loop),
        ),
    ):
        result = await AgenticLoop(
            store=_loop_store(),
            llm_client=MagicMock(),
            legacy_llm_client=MagicMock(),
        ).run_dual_llm_turn(context=context)

    domain.append_visible_message.assert_not_awaited()
    assert result.output_message_ids == ()


@pytest.mark.asyncio
async def test_dual_llm_user_turn_skips_silent_foreground_output() -> None:
    from app.core.companion_harness.companion.dual_llm_foreground_chat import (
        DualLlmForegroundChatResult,
    )

    domain = MagicMock(spec=OutputQueue)
    domain.append_visible_message = AsyncMock()
    context = _dual_llm_loop_context(
        output_queue=domain,
        companion_turn_track=CompanionTurnTrack.USER_CHAT,
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

    with (
        patch(
            "app.core.companion_harness.loop.agentic_loop.run_dual_llm_foreground_chat",
            new=AsyncMock(return_value=fg_result),
        ),
        patch(
            "app.core.companion_harness.loop.agentic_loop.run_tool_background_loop",
            new=AsyncMock(),
        ),
    ):
        result = await AgenticLoop(
            store=_loop_store(),
            llm_client=MagicMock(),
            legacy_llm_client=MagicMock(),
        ).run_dual_llm_turn(context=context)

    domain.append_visible_message.assert_not_awaited()
    assert result.output_message_ids == ()
