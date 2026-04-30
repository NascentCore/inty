"""Regression: companion turn groups LangSmith LLM runs under one parent trace."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.core.agentic_kernel.companion.llm_chat_runtime import (
    companion_turn_langsmith_parent_trace_id_str,
    create_companion_turn_root_run,
    end_companion_turn_root_run_safe,
)
from app.core.agentic_kernel.companion.llm_client import CompanionLLMConfig
from app.core.agentic_kernel.companion.memory_registry import get_memory_store
from app.core.agentic_kernel.companion.tool_background import start_tool_background_job
from app.core.agentic_kernel.companion.turn import run_turn


@patch(
    "app.core.agentic_kernel.companion.llm_chat_runtime.companion_turn_langsmith_parent_enabled",
    return_value=False,
)
def test_create_companion_turn_root_run_returns_none_when_disabled(_mock: MagicMock) -> None:
    assert (
        create_companion_turn_root_run(inty_trace_id="t1", user_msg_uuid="u1") is None
    )


@patch(
    "app.core.agentic_kernel.companion.llm_chat_runtime.companion_turn_langsmith_parent_enabled",
    return_value=True,
)
@patch("langsmith.run_trees.RunTree")
def test_create_companion_turn_root_run_builds_and_posts_run_tree(
    mock_rt_cls: MagicMock, _en: MagicMock
) -> None:
    mock_root = MagicMock()
    mock_rt_cls.return_value = mock_root
    out = create_companion_turn_root_run(inty_trace_id="t1", user_msg_uuid="u1")
    assert out is mock_root
    mock_rt_cls.assert_called_once()
    kwargs = mock_rt_cls.call_args.kwargs
    assert kwargs["name"] == "agentic_companion_user_turn"
    assert kwargs["inputs"]["inty_trace_id"] == "t1"
    assert kwargs["inputs"]["user_msg_uuid"] == "u1"
    mock_root.post.assert_called_once()
    end_companion_turn_root_run_safe(mock_root, ls_end_source="test_teardown")


def test_companion_turn_langsmith_parent_trace_id_str_empty_for_none() -> None:
    assert companion_turn_langsmith_parent_trace_id_str(None) == ""


def test_end_companion_turn_root_run_safe_noop_for_none() -> None:
    end_companion_turn_root_run_safe(None)


@patch("app.core.agentic_kernel.companion.tool_background.threading.Thread")
@patch("app.core.agentic_kernel.companion.tool_background._unregister_thread")
@patch("app.core.agentic_kernel.companion.tool_background.set_tool_background_db_loop")
@patch("app.core.agentic_kernel.companion.tool_background.clear_tool_background_db_loop")
@patch("asyncio.run")
@patch(
    "app.core.agentic_kernel.companion.tool_background.end_companion_turn_root_run_safe"
)
def test_start_tool_background_job_uses_set_tracing_parent_when_parent_given(
    mock_end: MagicMock,
    mock_asyncio_run: MagicMock,
    mock_clear_loop: MagicMock,
    mock_set_loop: MagicMock,
    mock_unreg: MagicMock,
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
        start_tool_background_job(
            ws_root=Path("/tmp/inty_ws"),
            request_messages=[{"role": "user", "content": "hi"}],
            tool_model_name="m",
            user_msg_uuid="uuid",
            trace_id="tr",
            tools=[],
            client=MagicMock(),
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


@patch("app.core.agentic_kernel.companion.tool_background.threading.Thread")
@patch("app.core.agentic_kernel.companion.tool_background._unregister_thread")
@patch("app.core.agentic_kernel.companion.tool_background.set_tool_background_db_loop")
@patch("app.core.agentic_kernel.companion.tool_background.clear_tool_background_db_loop")
@patch("asyncio.run")
@patch(
    "app.core.agentic_kernel.companion.tool_background.end_companion_turn_root_run_safe"
)
def test_start_tool_background_job_skips_set_tracing_parent_without_parent(
    mock_end: MagicMock,
    mock_asyncio_run: MagicMock,
    mock_clear_loop: MagicMock,
    mock_set_loop: MagicMock,
    mock_unreg: MagicMock,
    mock_thread: MagicMock,
) -> None:
    with patch("langsmith.run_helpers.set_tracing_parent") as mock_sp:
        mock_t = MagicMock()
        mock_thread.return_value = mock_t
        start_tool_background_job(
            ws_root=Path("/tmp/inty_ws"),
            request_messages=[{"role": "user", "content": "hi"}],
            tool_model_name="m",
            user_msg_uuid="uuid",
            trace_id="tr",
            tools=[],
            client=MagicMock(),
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
            default_model="m/default",
            chat_model="m/chat",
            tool_model="m/tool",
            enable_async_tool_background=True,
            async_chat_front_timeout_sec=120.0,
        )
        self.chat_calls: list[dict[str, Any]] = []

    def _resolve_model(self, role: str) -> str:
        return f"m/{role}"

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

    def complete_text(
        self, messages: list[dict[str, Any]], *, model_role: str = "memory"
    ) -> str:
        return ""


@pytest.mark.asyncio
async def test_run_turn_async_dual_passes_langsmith_parent_run_kwarg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path
    store = get_memory_store(root)
    store.write_document("context.json", '{"context_mode": "intimate"}\n')
    store.write_document("IDENTITY.md", "id\n")
    store.write_document("SOUL.md", "s\n")
    store.write_document("USER.md", "u\n")
    store.write_document("MEMORY.md", "m\n")
    store.write_document("transcript.jsonl", "")

    sentinel = MagicMock()

    def _fake_create_root(**kwargs: Any) -> MagicMock:
        return sentinel

    monkeypatch.setattr(
        "app.core.agentic_kernel.companion.turn.create_companion_turn_root_run",
        _fake_create_root,
    )

    bg_jobs: list[dict[str, Any]] = []

    def _capture_bg(**kwargs: Any) -> None:
        bg_jobs.append(kwargs)

    monkeypatch.setattr(
        "app.core.agentic_kernel.companion.turn.start_tool_background_job",
        _capture_bg,
    )

    client = _FakeAsyncDualLLMClient()
    await run_turn(
        root,
        "hello async dual langsmith",
        store=store,
        llm_client=client,  # type: ignore[arg-type]
        defer_memory_update=True,
        memory_config=None,
    )

    assert len(bg_jobs) == 1
    assert bg_jobs[0]["langsmith_parent_run"] is sentinel
