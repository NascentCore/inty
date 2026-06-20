"""Regression: companion turn groups LangSmith LLM runs under one parent trace."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.core.companion_harness.llm.chat_completions import create_chat_completion_sync
from app.core.companion_harness.companion.llm_chat_runtime import (
    companion_turn_langsmith_parent_trace_id_str,
    create_companion_turn_root_run,
    end_companion_turn_root_run_safe,
)
from app.core.llms.client import CompanionLLMConfig
from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    InnerTickActivity,
)
from app.core.companion_harness.companion.langsmith_turn_slice import (
    CompanionTurnLangsmithSlice,
    LangsmithChannelSource,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.tools.tool_background import start_tool_background_job
from app.core.companion_harness.companion.turn import run_companion_user_chat_turn
from app.core.companion_harness.companion.turn_deps import CompanionTurnDeps
from app.utils.config import CompanionMemoryBootstrapType
from app.utils.models_catalog import GenAIModel, resolve_chat_text_model

_APP_SLICE = CompanionTurnLangsmithSlice.app_default()


def _idle_tool_bg() -> threading.Event:
    ev = threading.Event()
    ev.set()
    return ev


@patch(
    "app.core.companion_harness.companion.llm_chat_runtime.companion_turn_langsmith_parent_enabled",
    return_value=False,
)
def test_create_companion_turn_root_run_returns_none_when_disabled(_mock: MagicMock) -> None:
    assert (
        create_companion_turn_root_run(
            inty_trace_id="t1",
            user_msg_uuid="u1",
            chat_model=resolve_chat_text_model("stub/disabled-chat"),
            tool_model=resolve_chat_text_model("stub/disabled-tool"),
            langsmith_slice=_APP_SLICE,
        )
        is None
    )


@patch(
    "app.core.companion_harness.companion.llm_chat_runtime.companion_turn_langsmith_parent_enabled",
    return_value=True,
)
def test_create_companion_turn_root_run_skips_kernel_placeholder_models(
    _en: MagicMock,
) -> None:
    assert (
        create_companion_turn_root_run(
            inty_trace_id="t1",
            user_msg_uuid="u1",
            chat_model=resolve_chat_text_model("m/chat"),
            tool_model=resolve_chat_text_model("m/tool"),
            langsmith_slice=_APP_SLICE,
        )
        is None
    )


@patch(
    "app.core.companion_harness.companion.llm_chat_runtime.companion_turn_langsmith_parent_enabled",
    return_value=True,
)
@patch("langsmith.run_trees.RunTree")
def test_create_companion_turn_root_run_builds_and_posts_run_tree(
    mock_rt_cls: MagicMock, _en: MagicMock
) -> None:
    mock_root = MagicMock()
    mock_rt_cls.return_value = mock_root
    out = create_companion_turn_root_run(
        inty_trace_id="t1",
        user_msg_uuid="u1",
        chat_model=resolve_chat_text_model("stub/chat-route"),
        tool_model=resolve_chat_text_model("stub/tool-route"),
        user_id="u-42",
        companion_id="c-7",
        langsmith_slice=_APP_SLICE,
    )
    assert out is mock_root
    mock_rt_cls.assert_called_once()
    kwargs = mock_rt_cls.call_args.kwargs
    assert kwargs["name"] == "agentic_companion_user_turn user=u-42 agent=c-7"
    assert kwargs["tags"] == [
        "agentic_companion",
        "user_turn",
        "explicit_user_message",
        "runtime_channel_app",
    ]
    assert kwargs["inputs"]["inty_trace_id"] == "t1"
    assert kwargs["inputs"]["user_msg_uuid"] == "u1"
    assert kwargs["inputs"]["chat_model"] == "stub/chat-route"
    assert kwargs["inputs"]["tool_model"] == "stub/tool-route"
    assert isinstance(kwargs["inputs"]["chat_model_catalog"], dict)
    assert isinstance(kwargs["inputs"]["tool_model_catalog"], dict)
    assert kwargs["inputs"]["user_id"] == "u-42"
    assert kwargs["inputs"]["companion_id"] == "c-7"
    assert kwargs["inputs"]["inty_turn_lane"] == "explicit_user_message"
    assert "inner_tick_activity" not in kwargs["inputs"]
    assert kwargs["extra"]["metadata"]["ls_model_name"] == "stub/chat-route | stub/tool-route"
    assert kwargs["extra"]["metadata"]["inty_user_id"] == "u-42"
    assert kwargs["extra"]["metadata"]["inty_companion_id"] == "c-7"
    assert kwargs["extra"]["metadata"]["inty_turn_lane"] == "explicit_user_message"
    assert "inner_tick_activity" not in kwargs["extra"]["metadata"]
    mock_root.post.assert_called_once()
    end_companion_turn_root_run_safe(mock_root, ls_end_source="test_teardown")


@patch(
    "app.core.companion_harness.companion.llm_chat_runtime.companion_turn_langsmith_parent_enabled",
    return_value=True,
)
@patch("langsmith.run_trees.RunTree")
def test_create_companion_turn_root_run_name_uses_unknown_when_ids_empty(
    mock_rt_cls: MagicMock, _en: MagicMock
) -> None:
    mock_root = MagicMock()
    mock_rt_cls.return_value = mock_root
    create_companion_turn_root_run(
        inty_trace_id="t1",
        user_msg_uuid="u1",
        chat_model=resolve_chat_text_model("stub/chat-route"),
        tool_model=resolve_chat_text_model("stub/tool-route"),
        langsmith_slice=_APP_SLICE,
    )
    kwargs = mock_rt_cls.call_args.kwargs
    assert kwargs["name"] == "agentic_companion_user_turn user=unknown agent=unknown"
    assert kwargs["inputs"]["user_id"] == ""
    assert kwargs["inputs"]["companion_id"] == ""
    assert kwargs["inputs"]["inty_turn_lane"] == "explicit_user_message"
    end_companion_turn_root_run_safe(mock_root, ls_end_source="test_teardown")


@patch(
    "app.core.companion_harness.companion.llm_chat_runtime.companion_turn_langsmith_parent_enabled",
    return_value=True,
)
@patch("langsmith.run_trees.RunTree")
def test_create_companion_turn_root_run_implicit_signed_on_lane(
    mock_rt_cls: MagicMock, _en: MagicMock
) -> None:
    mock_root = MagicMock()
    mock_rt_cls.return_value = mock_root
    create_companion_turn_root_run(
        inty_trace_id="t1",
        user_msg_uuid="u1",
        chat_model=resolve_chat_text_model("stub/chat-route"),
        tool_model=resolve_chat_text_model("stub/tool-route"),
        user_id="u1",
        companion_id="a1",
        implicit_user_signed_on=True,
        langsmith_slice=_APP_SLICE,
    )
    kwargs = mock_rt_cls.call_args.kwargs
    assert kwargs["name"] == "agentic_companion_implicit_turn user=u1 agent=a1"
    assert kwargs["tags"] == [
        "agentic_companion",
        "implicit_turn",
        "implicit_user_signed_on",
        "runtime_channel_app",
    ]
    assert kwargs["inputs"]["inty_turn_lane"] == "implicit_turn"
    assert kwargs["inputs"]["implicit_signal"] == "implicit_user_signed_on"
    assert kwargs["extra"]["metadata"]["inty_turn_lane"] == "implicit_turn"
    assert kwargs["extra"]["metadata"]["implicit_signal"] == "implicit_user_signed_on"
    end_companion_turn_root_run_safe(mock_root, ls_end_source="test_teardown")


@patch(
    "app.core.companion_harness.companion.llm_chat_runtime.companion_turn_langsmith_parent_enabled",
    return_value=True,
)
@patch("langsmith.run_trees.RunTree")
def test_create_companion_turn_root_run_inner_tick_maintenance_lane(
    mock_rt_cls: MagicMock, _en: MagicMock
) -> None:
    mock_root = MagicMock()
    mock_rt_cls.return_value = mock_root
    create_companion_turn_root_run(
        inty_trace_id="t1",
        user_msg_uuid="u1",
        chat_model=resolve_chat_text_model("stub/chat-route"),
        tool_model=resolve_chat_text_model("stub/tool-route"),
        user_id="u1",
        companion_id="a1",
        inner_tick_turn=True,
        inner_tick_activity=InnerTickActivity.MAINTENANCE,
        transcript_newest_message_uuid="tail-uuid-1",
        langsmith_slice=_APP_SLICE,
    )
    kwargs = mock_rt_cls.call_args.kwargs
    assert kwargs["name"] == "agentic_companion_inner_tick maintenance user=u1 agent=a1"
    assert kwargs["tags"] == [
        "agentic_companion",
        "inner_tick",
        "runtime_channel_app",
    ]
    assert kwargs["inputs"]["inty_turn_lane"] == "inner_tick"
    assert kwargs["inputs"]["inner_tick_activity"] == "maintenance"
    assert kwargs["inputs"]["transcript_newest_message_uuid"] == "tail-uuid-1"
    assert kwargs["extra"]["metadata"]["inty_turn_lane"] == "inner_tick"
    assert kwargs["extra"]["metadata"]["inner_tick_activity"] == "maintenance"
    assert kwargs["extra"]["metadata"]["transcript_newest_message_uuid"] == "tail-uuid-1"
    end_companion_turn_root_run_safe(mock_root, ls_end_source="test_teardown")


@patch(
    "app.core.companion_harness.companion.llm_chat_runtime.companion_turn_langsmith_parent_enabled",
    return_value=True,
)
@patch("langsmith.run_trees.RunTree")
def test_create_companion_turn_root_run_inner_tick_proactive_lane(
    mock_rt_cls: MagicMock, _en: MagicMock
) -> None:
    mock_root = MagicMock()
    mock_rt_cls.return_value = mock_root
    create_companion_turn_root_run(
        inty_trace_id="t1",
        user_msg_uuid="u1",
        chat_model=resolve_chat_text_model("stub/chat-route"),
        tool_model=resolve_chat_text_model("stub/tool-route"),
        user_id="u1",
        companion_id="a1",
        inner_tick_turn=True,
        inner_tick_activity=InnerTickActivity.PROACTIVE_CHAT,
        transcript_newest_message_uuid="tail-uuid-2",
        langsmith_slice=_APP_SLICE,
    )
    kwargs = mock_rt_cls.call_args.kwargs
    assert kwargs["name"] == "agentic_companion_inner_tick proactive_chat user=u1 agent=a1"
    assert kwargs["inputs"]["inner_tick_activity"] == "proactive_chat"
    assert kwargs["inputs"]["transcript_newest_message_uuid"] == "tail-uuid-2"
    assert kwargs["extra"]["metadata"]["inner_tick_activity"] == "proactive_chat"
    assert kwargs["extra"]["metadata"]["transcript_newest_message_uuid"] == "tail-uuid-2"
    end_companion_turn_root_run_safe(mock_root, ls_end_source="test_teardown")


@patch(
    "app.core.companion_harness.companion.llm_chat_runtime.companion_turn_langsmith_parent_enabled",
    return_value=True,
)
@patch("langsmith.run_trees.RunTree")
def test_create_companion_turn_root_run_includes_runtime_channel(
    mock_rt_cls: MagicMock, _en: MagicMock
) -> None:
    mock_root = MagicMock()
    mock_rt_cls.return_value = mock_root
    telegram_slice = CompanionTurnLangsmithSlice.from_channel(
        CompanionRuntimeChannel.TELEGRAM,
        LangsmithChannelSource.EXPLICIT_TURN,
    )
    create_companion_turn_root_run(
        inty_trace_id="t1",
        user_msg_uuid="u1",
        chat_model=resolve_chat_text_model("stub/chat-route"),
        tool_model=resolve_chat_text_model("stub/tool-route"),
        user_id="u1",
        companion_id="a1",
        langsmith_slice=telegram_slice,
    )
    kwargs = mock_rt_cls.call_args.kwargs
    assert kwargs["inputs"]["runtime_channel"] == "telegram"
    assert "runtime_channel_telegram" in kwargs["tags"]
    assert kwargs["extra"]["metadata"]["inty_runtime_channel"] == "telegram"
    assert (
        kwargs["extra"]["metadata"]["inty_runtime_channel_source"]
        == LangsmithChannelSource.EXPLICIT_TURN.value
    )
    end_companion_turn_root_run_safe(mock_root, ls_end_source="test_teardown")


@patch(
    "app.core.companion_harness.companion.llm_chat_runtime.companion_turn_langsmith_parent_enabled",
    return_value=True,
)
@patch("langsmith.run_trees.RunTree")
def test_create_companion_turn_root_run_inner_tick_dreaming_lane(
    mock_rt_cls: MagicMock, _en: MagicMock
) -> None:
    mock_root = MagicMock()
    mock_rt_cls.return_value = mock_root
    create_companion_turn_root_run(
        inty_trace_id="t1",
        user_msg_uuid="boundary-u1",
        chat_model=resolve_chat_text_model("stub/chat-route"),
        tool_model=resolve_chat_text_model("stub/tool-route"),
        user_id="u1",
        companion_id="a1",
        inner_tick_turn=True,
        inner_tick_activity=InnerTickActivity.DREAMING,
        transcript_newest_message_uuid="boundary-u1",
        langsmith_slice=_APP_SLICE,
    )
    kwargs = mock_rt_cls.call_args.kwargs
    assert kwargs["name"] == "agentic_companion_inner_tick dreaming user=u1 agent=a1"
    assert kwargs["inputs"]["inner_tick_activity"] == "dreaming"
    assert kwargs["inputs"]["transcript_newest_message_uuid"] == "boundary-u1"
    assert kwargs["extra"]["metadata"]["inner_tick_activity"] == "dreaming"
    end_companion_turn_root_run_safe(mock_root, ls_end_source="test_teardown")


def test_companion_turn_langsmith_parent_trace_id_str_empty_for_none() -> None:
    assert companion_turn_langsmith_parent_trace_id_str(None) == ""


def test_end_companion_turn_root_run_safe_noop_for_none() -> None:
    end_companion_turn_root_run_safe(None)


@patch("app.core.companion_harness.tools.tool_background.threading.Thread")
@patch("app.core.companion_harness.tools.tool_background.set_tool_background_db_loop")
@patch("app.core.companion_harness.tools.tool_background.clear_tool_background_db_loop")
@patch("asyncio.run")
@patch(
    "app.core.companion_harness.tools.tool_background.end_companion_turn_root_run_safe"
)
def test_start_tool_background_job_uses_set_tracing_parent_when_parent_given(
    mock_end: MagicMock,
    mock_asyncio_run: MagicMock,
    _mock_clear_loop: MagicMock,
    _mock_set_loop: MagicMock,
    mock_thread: MagicMock,
) -> None:
    parent = MagicMock()
    entered: list[bool] = []

    class _CM:
        def __enter__(self) -> None:
            entered.append(True)

        def __exit__(self, *args: object) -> bool:
            return False

    def _fake_set_parent(run: object) -> _CM:
        assert run is parent
        return _CM()

    with patch(
        "langsmith.run_helpers.set_tracing_parent",
        side_effect=_fake_set_parent,
    ):
        mock_t = MagicMock()
        mock_thread.return_value = mock_t
        st = MemoryStore(scope=CompanionScope("u", "a", "c"), repository=None)
        start_tool_background_job(
            memory_store=st,
            request_messages=[{"role": "user", "content": "hi"}],
            tool_model=resolve_chat_text_model("m"),
            user_msg_uuid="uuid",
            trace_id="tr",
            tools=[],
            client=MagicMock(),
            companion_turn_track=CompanionTurnTrack.USER_CHAT,
            langsmith_parent_run=parent,
        )
        runner = mock_thread.call_args.kwargs["target"]
        runner()

    assert entered == [True]
    mock_asyncio_run.assert_called_once()
    coro = mock_asyncio_run.call_args[0][0]
    coro.close()
    mock_end.assert_called_once_with(
        parent, error=None, ls_end_source="tool_background_thread"
    )


@patch("app.core.companion_harness.tools.tool_background.threading.Thread")
@patch("app.core.companion_harness.tools.tool_background.set_tool_background_db_loop")
@patch("app.core.companion_harness.tools.tool_background.clear_tool_background_db_loop")
@patch("asyncio.run")
@patch(
    "app.core.companion_harness.tools.tool_background.end_companion_turn_root_run_safe"
)
def test_start_tool_background_job_skips_set_tracing_parent_without_parent(
    mock_end: MagicMock,
    mock_asyncio_run: MagicMock,
    _mock_clear_loop: MagicMock,
    _mock_set_loop: MagicMock,
    mock_thread: MagicMock,
) -> None:
    with patch("langsmith.run_helpers.set_tracing_parent") as mock_sp:
        mock_t = MagicMock()
        mock_thread.return_value = mock_t
        st = MemoryStore(scope=CompanionScope("u", "a", "c"), repository=None)
        start_tool_background_job(
            memory_store=st,
            request_messages=[{"role": "user", "content": "hi"}],
            tool_model=resolve_chat_text_model("m"),
            user_msg_uuid="uuid",
            trace_id="tr",
            tools=[],
            client=MagicMock(),
            companion_turn_track=CompanionTurnTrack.USER_CHAT,
        )
        runner = mock_thread.call_args.kwargs["target"]
        runner()

    mock_sp.assert_not_called()
    mock_asyncio_run.assert_called_once()
    mock_asyncio_run.call_args[0][0].close()
    mock_end.assert_called_once_with(
        None, error=None, ls_end_source="tool_background_thread"
    )


class _FakeAsyncDualLLMClient:
    def __init__(self) -> None:
        self.config = CompanionLLMConfig(
            api_key="k",
            default_model=resolve_chat_text_model("m/default"),
            chat_model=resolve_chat_text_model("m/chat"),
            tool_model=resolve_chat_text_model("m/tool"),
            async_chat_front_timeout_sec=120.0,
        )
        self.chat_calls: list[dict[str, Any]] = []

    def resolve_model(self, role: str) -> GenAIModel:
        return resolve_chat_text_model(f"m/{role}")

    def chat_completion(self, **kwargs: Any) -> Any:
        self.chat_calls.append(kwargs)
        env = {
            "user_facing_reply": "foreground ok",
            "importance_round": 5,
            "importance_user_message": 5,
            "importance_assistant_message": 5,
        }
        msg = SimpleNamespace(
            content=json.dumps(env),
            tool_calls=[],
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    def sync_client_for_route(self, route: str) -> object:
        return object()

    @property
    def chat_completions_sync(self):
        return create_chat_completion_sync

    def complete_text(
        self, messages: list[dict[str, Any]], *, model_role: str = "memory"
    ) -> str:
        return ""


@pytest.mark.asyncio
async def test_run_turn_async_dual_passes_langsmith_parent_run_kwarg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = MemoryStore(
        scope=CompanionScope("ls", "agent", str(tmp_path.resolve())),
        repository=None,
    )
    store.write_document("context.json", '{"context_mode": "intimate"}\n')
    store.write_document("IDENTITY.md", "id\n")
    store.write_document("SOUL.md", "s\n")
    store.write_document("USER.md", "u\n")
    store.write_document("MEMORY.md", "m\n")
    store.write_document("transcript.jsonl", "")

    sentinel = MagicMock()
    parent_kwargs: list[dict[str, Any]] = []

    def _fake_create_root(**kwargs: Any) -> MagicMock:
        parent_kwargs.append(kwargs)
        return sentinel

    monkeypatch.setattr(
        "app.core.companion_harness.companion.turn.create_companion_turn_root_run",
        _fake_create_root,
    )

    bg_jobs: list[dict[str, Any]] = []

    def _capture_bg(**kwargs: Any) -> None:
        bg_jobs.append(kwargs)

    monkeypatch.setattr(
        "app.core.companion_harness.companion.turn.start_tool_background_job",
        _capture_bg,
    )

    client = _FakeAsyncDualLLMClient()
    await run_companion_user_chat_turn(
        "hello async dual langsmith",
        deps=CompanionTurnDeps(
            store=store,
            llm_client=client,  # type: ignore[arg-type]
            transcript_compaction=None,
            transcript_llm_window_max_messages=None,
            repository_only_store_text=False,
            memory_bootstrap_type=CompanionMemoryBootstrapType.NONE.value,
            runtime_context=TurnRuntimeContext(
                channel=CompanionRuntimeChannel.TELEGRAM,
                implicit_signal_bundle=None,
            ),
            background_output_sink=None,
            preset_user_msg_uuid=None,
            langsmith_parent_run_enabled=None,
            tool_bg_idle_event=_idle_tool_bg(),
            bootstrap_interim_output_sink=None,
        ),
    )

    assert len(bg_jobs) == 1
    assert bg_jobs[0]["langsmith_parent_run"] is sentinel
    assert bg_jobs[0]["chat_completions_sync"] is client.chat_completions_sync
    assert len(parent_kwargs) == 1
    slice_ = parent_kwargs[0]["langsmith_slice"]
    assert slice_.runtime_channel == CompanionRuntimeChannel.TELEGRAM
    assert slice_.channel_source == LangsmithChannelSource.EXPLICIT_TURN
    assert len(client.chat_calls) == 1
    fg_meta = client.chat_calls[0]["langsmith_extra"]["metadata"]
    assert fg_meta["inty_runtime_channel"] == "telegram"
    assert fg_meta["inty_runtime_channel_source"] == "explicit_turn"
