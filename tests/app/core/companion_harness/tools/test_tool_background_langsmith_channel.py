"""LangSmith runtime_channel wiring for tool_background sync completions."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.core.companion_harness.companion.langsmith_turn_slice import (
    CompanionTurnLangsmithSlice,
    LangsmithChannelSource,
)
from app.core.companion_harness.companion.models import CompanionTurnTrack
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.llm.langsmith_invocation_extra import (
    SOURCE_TOOL_BACKGROUND_CONTINUE,
    SOURCE_TOOL_BACKGROUND_INITIAL,
)
from app.utils.models_catalog import resolve_chat_text_model
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)
from app.core.companion_harness.tools.tool_background import (
    _initial_tool_bg_completion_with_fallbacks,
    run_tool_background_loop,
)


def _tool_call_response() -> MagicMock:
    tool_call = MagicMock()
    tool_call.id = "tc1"
    tool_call.function.name = "memory_store_write_document"
    tool_call.function.arguments = "{}"
    message = MagicMock()
    message.tool_calls = [tool_call]
    message.content = ""
    choice = MagicMock()
    choice.message = message
    choice.finish_reason = "tool_calls"
    response = MagicMock()
    response.choices = [choice]
    return response


def _envelope_response() -> MagicMock:
    envelope = {
        "user_facing_reply": "",
        "importance_round": 5,
        "importance_user_message": 5,
        "importance_assistant_message": 5,
        "output_to_user": False,
    }
    message = MagicMock()
    message.tool_calls = []
    message.content = json.dumps(envelope)
    choice = MagicMock()
    choice.message = message
    choice.finish_reason = "stop"
    response = MagicMock()
    response.choices = [choice]
    return response


def test_initial_tool_bg_completion_sync_receives_telegram_channel() -> None:
    sync_calls: list[dict[str, Any]] = []

    def fake_sync(
        _client: object,
        *,
        model: str,
        messages_payload: list[dict[str, Any]],
        tools: list[Any],
        tool_choice: str | None,
        response_format: object,
        langsmith_extra: dict[str, Any],
        high_reasoning: bool,
    ) -> MagicMock:
        sync_calls.append(
            {
                "model": model,
                "tool_choice": tool_choice,
                "langsmith_extra": langsmith_extra,
            }
        )
        return _tool_call_response()

    telegram_slice = CompanionTurnLangsmithSlice.from_channel(
        ChannelKind.TELEGRAM,
        LangsmithChannelSource.EXPLICIT_TURN,
    )
    _initial_tool_bg_completion_with_fallbacks(
        object(),
        fake_sync,
        model="m/tool",
        messages_payload=[{"role": "user", "content": "hi"}],
        tools=[],
        force_tools=False,
        langsmith_slice=telegram_slice,
    )

    assert len(sync_calls) == 1
    extra = sync_calls[0]["langsmith_extra"]
    assert extra["name"] == SOURCE_TOOL_BACKGROUND_INITIAL
    assert extra["metadata"]["inty_runtime_channel"] == "telegram"
    assert extra["metadata"]["inty_runtime_channel_source"] == "explicit_turn"


@pytest.mark.asyncio
async def test_run_background_tool_loop_continue_sync_receives_telegram_channel(
    tmp_path: Path,
) -> None:
    sync_calls: list[dict[str, Any]] = []

    def fake_sync(
        _client: object,
        *,
        model: str,
        messages_payload: list[dict[str, Any]],
        tools: list[Any] | None = None,
        tool_choice: str | None = None,
        response_format: object = None,
        langsmith_extra: dict[str, Any] | None = None,
        high_reasoning: bool = False,
    ) -> MagicMock:
        sync_calls.append(
            {
                "model": model,
                "langsmith_extra": langsmith_extra,
            }
        )
        if len(sync_calls) == 1:
            return _tool_call_response()
        return _envelope_response()

    async def fake_execute_tool_call(
        _store: MemoryStore,
        _name: str,
        _raw_arguments: str,
        *,
        write_allowlist: frozenset[str],
        repository_only_store_text: bool,
    ) -> tuple[str, str | None]:
        return "OK", None

    store = MemoryStore(
        scope=CompanionScope("u", "a", str(tmp_path.resolve())),
        repository=None,
    )
    p = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    store.write_document(p.context_json, '{"context_mode": "intimate"}\n')
    store.write_document(p.identity, "id\n")
    store.write_document(p.soul, "soul\n")
    store.write_document(p.user_md, "user\n")
    store.write_document(p.memory_md, "memory\n")
    store.write_document(p.transcript, "")

    await run_tool_background_loop(
        memory_store=store,
        request_messages=[{"role": "user", "content": "hi"}],
        tool_model=resolve_chat_text_model("m/tool"),
        user_msg_uuid="uuid-bg",
        trace_id="trace-bg",
        tools=[],
        on_event=lambda _event: None,
        execute_tool_call_fn=fake_execute_tool_call,
        client=object(),
        chat_completion_sync=fake_sync,
        companion_turn_track=CompanionTurnTrack.USER_CHAT,
        llm_round_timeout_sec=1.0,
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.TELEGRAM,
            implicit_signal_bundle=None,
        ),
        langsmith_slice=CompanionTurnLangsmithSlice.from_runtime_context(
            TurnRuntimeContext(
                channel=ChannelKind.TELEGRAM,
                implicit_signal_bundle=None,
            )
        ),
        force_tools_first_round=False,
    )

    assert len(sync_calls) >= 2
    initial_extra = sync_calls[0]["langsmith_extra"]
    assert initial_extra is not None
    assert initial_extra["name"] == SOURCE_TOOL_BACKGROUND_INITIAL
    assert initial_extra["metadata"]["inty_runtime_channel"] == "telegram"

    continue_extra = sync_calls[1]["langsmith_extra"]
    assert continue_extra is not None
    assert continue_extra["name"] == SOURCE_TOOL_BACKGROUND_CONTINUE
    assert continue_extra["metadata"]["inty_runtime_channel"] == "telegram"
    assert (
        continue_extra["metadata"]["inty_runtime_channel_source"]
        == "explicit_turn"
    )


@pytest.mark.asyncio
async def test_run_background_tool_loop_initial_round_timeout_returns(
    tmp_path: Path,
) -> None:
    sync_calls = 0
    events: list[object] = []

    def slow_sync(
        _client: object,
        *,
        model: str,
        messages_payload: list[dict[str, Any]],
        tools: list[Any] | None = None,
        tool_choice: str | None = None,
        response_format: object = None,
        langsmith_extra: dict[str, Any] | None = None,
        high_reasoning: bool = False,
    ) -> MagicMock:
        nonlocal sync_calls
        sync_calls += 1
        time.sleep(0.05)
        return _envelope_response()

    async def fake_execute_tool_call(
        _store: MemoryStore,
        _name: str,
        _raw_arguments: str,
        *,
        write_allowlist: frozenset[str],
        repository_only_store_text: bool,
    ) -> tuple[str, str | None]:
        return "OK", None

    store = MemoryStore(
        scope=CompanionScope("u", "a", str(tmp_path.resolve())),
        repository=None,
    )
    store.write_document(DEFAULT_MEMORY_STORE_SCOPE_PATHS.context_json, "{}\n")
    await run_tool_background_loop(
        memory_store=store,
        request_messages=[{"role": "user", "content": "hi"}],
        tool_model=resolve_chat_text_model("m/tool"),
        user_msg_uuid="uuid-bg-timeout",
        trace_id="trace-bg-timeout",
        tools=[],
        on_event=events.append,
        execute_tool_call_fn=fake_execute_tool_call,
        client=object(),
        chat_completion_sync=slow_sync,
        companion_turn_track=CompanionTurnTrack.USER_CHAT,
        llm_round_timeout_sec=0.01,
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        ),
        langsmith_slice=CompanionTurnLangsmithSlice.from_runtime_context(
            TurnRuntimeContext(
                channel=ChannelKind.APP_WS,
                implicit_signal_bundle=None,
            )
        ),
        force_tools_first_round=False,
    )

    assert sync_calls == 1
    assert events == []


@pytest.mark.asyncio
async def test_run_background_tool_loop_continue_round_timeout_returns(
    tmp_path: Path,
) -> None:
    sync_calls = 0
    events: list[object] = []

    def fake_sync(
        _client: object,
        *,
        model: str,
        messages_payload: list[dict[str, Any]],
        tools: list[Any] | None = None,
        tool_choice: str | None = None,
        response_format: object = None,
        langsmith_extra: dict[str, Any] | None = None,
        high_reasoning: bool = False,
    ) -> MagicMock:
        nonlocal sync_calls
        sync_calls += 1
        if sync_calls == 1:
            return _tool_call_response()
        time.sleep(0.05)
        return _envelope_response()

    async def fake_execute_tool_call(
        _store: MemoryStore,
        _name: str,
        _raw_arguments: str,
        *,
        write_allowlist: frozenset[str],
        repository_only_store_text: bool,
    ) -> tuple[str, str | None]:
        return "OK", None

    store = MemoryStore(
        scope=CompanionScope("u", "a", str(tmp_path.resolve())),
        repository=None,
    )
    store.write_document(DEFAULT_MEMORY_STORE_SCOPE_PATHS.context_json, "{}\n")
    await run_tool_background_loop(
        memory_store=store,
        request_messages=[{"role": "user", "content": "hi"}],
        tool_model=resolve_chat_text_model("m/tool"),
        user_msg_uuid="uuid-bg-continue-timeout",
        trace_id="trace-bg-continue-timeout",
        tools=[],
        on_event=events.append,
        execute_tool_call_fn=fake_execute_tool_call,
        client=object(),
        chat_completion_sync=fake_sync,
        companion_turn_track=CompanionTurnTrack.USER_CHAT,
        llm_round_timeout_sec=0.01,
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        ),
        langsmith_slice=CompanionTurnLangsmithSlice.from_runtime_context(
            TurnRuntimeContext(
                channel=ChannelKind.APP_WS,
                implicit_signal_bundle=None,
            )
        ),
        force_tools_first_round=False,
    )

    assert sync_calls == 2
    assert events == []
