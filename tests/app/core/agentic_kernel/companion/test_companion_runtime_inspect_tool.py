from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.core.agentic_kernel.companion import runtime_inspect_context as ric
from app.core.agentic_kernel.companion.llm_chat_runtime import tool_path_chat_completion_kwargs
from app.core.agentic_kernel.companion.llm_client import CompanionLLMClient, CompanionLLMConfig
from app.core.agentic_kernel.companion.memory_pipeline import MemoryPipelineConfig
from app.core.agentic_kernel.companion.memory_registry import get_memory_store
from app.core.agentic_kernel.companion.models import ContextMeta, InnerTickMode
from app.core.agentic_kernel.companion.runtime_inspect_context import (
    build_last_chat_completion_request_payload,
    build_turn_runtime_config_dict,
    runtime_inspect_begin_turn,
    runtime_inspect_end_turn,
    runtime_inspect_set_last_chat_completion_request,
    runtime_inspect_set_runtime_config,
)
from app.core.agentic_kernel.companion.runtime_events import append_runtime_event
from app.core.agentic_kernel.companion.companion_tool_runtime import (
    WORKSPACE_READ_FILE_MAX_CHARS_CAP,
    execute_tool_call,
)
from app.core.agentic_kernel.companion.runtime_inspect_tool import tool_companion_runtime_inspect
from app.core.agentic_kernel.companion.prompts.system_messages import (
    build_system_prompt,
)


def _run_tool(root: Path, name: str, args: str) -> str:
    return asyncio.run(execute_tool_call(root, name, args))


def test_companion_runtime_inspect_outside_scope(tmp_path: Path) -> None:
    root = tmp_path
    get_memory_store(root)
    out = _run_tool(root, "companion_runtime_inspect", "{}")
    data = json.loads(out)
    assert "runtime_unavailable_reason" in data
    assert data["runtime_config"] is None
    assert data["last_chat_completion_request"] is None


def test_companion_runtime_inspect_with_contextvar(tmp_path: Path) -> None:
    root = tmp_path
    store = get_memory_store(root)
    store.write_document("SOUL.md", "soul-content-here")
    append_runtime_event(
        store,
        {"ts": "2026-05-08T00:00:00Z", "kind": "tool_timeout", "detail": "slow"},
    )
    token = runtime_inspect_begin_turn()
    try:
        client = CompanionLLMClient(
            CompanionLLMConfig(
                api_key="super-secret-key",
                default_model="test/model-a",
                api_base="https://example.invalid/v1",
            )
        )
        runtime_inspect_set_runtime_config(
            build_turn_runtime_config_dict(
                llm_client=client,
                mem_cfg=MemoryPipelineConfig(),
                context=ContextMeta(context_mode="intimate"),
                transcript_llm_window_max_messages=12,
                inner_tick_turn=False,
                inner_tick_mode=InnerTickMode.MAINTENANCE,
                repository_only_workspace_text=True,
                transcript_compaction=None,
                workspace_read_file_max_chars_cap=WORKSPACE_READ_FILE_MAX_CHARS_CAP,
            )
        )
        runtime_inspect_set_last_chat_completion_request(
            build_last_chat_completion_request_payload(
                model="test/model-a",
                messages=[
                    {"role": "system", "content": "system text"},
                    {"role": "user", "content": "hello"},
                ],
                tools=None,
            )
        )
        out = _run_tool(root, "companion_runtime_inspect", "{}")
        data = json.loads(out)
        assert data["runtime_config"]["llm"]["api_key"] == "***"
        assert "super-secret-key" not in out
        assert data["last_chat_completion_request"]["model"] == "test/model-a"
        msgs = data["last_chat_completion_request"]["messages"]
        assert msgs[0]["role"] == "system"
        assert msgs[1]["content"] == "hello"
        assert (
            data["last_chat_completion_request"]["openrouter_extra_body"]
            == tool_path_chat_completion_kwargs("test/model-a")
        )
        assert "SOUL.md" in data["store_documents"]
        assert "soul-content-here" in data["store_documents"]["SOUL.md"]["text"]
        assert data["runtime_events"] == [
            {
                "ts": "2026-05-08T00:00:00Z",
                "kind": "tool_timeout",
                "detail": "slow",
            }
        ]
    finally:
        runtime_inspect_end_turn(token)


def test_companion_runtime_inspect_thread_overlay(tmp_path: Path) -> None:
    ric.runtime_inspect_thread_overlay_begin(
        {
            "runtime_config": {"source": "tool_background", "tool_model_name": "bg/model"},
            "last_chat_completion_request": None,
        }
    )
    try:
        ric.runtime_inspect_set_last_chat_completion_request(
            build_last_chat_completion_request_payload(
                model="bg/model",
                messages=[{"role": "user", "content": "bg-user"}],
                tools=[],
            )
        )
        out = tool_companion_runtime_inspect(tmp_path, {"include_store_documents": False})
        data = json.loads(out)
        assert data["runtime_config"]["source"] == "tool_background"
        assert data["last_chat_completion_request"]["messages"][-1]["content"] == "bg-user"
        assert "store_documents" not in data
    finally:
        ric.runtime_inspect_thread_overlay_end()


def test_build_system_prompt_tools_contract_mentions_inspect() -> None:
    from app.core.agentic_kernel.companion.models import PromptBundle

    text = build_system_prompt(
        PromptBundle(
            identity="i",
            soul="s",
            user_md="u",
            memory_md="m",
        ),
        ContextMeta(),
        enable_tools=True,
    )
    assert "companion_runtime_inspect" in text
    assert "（6）" in text


def test_tool_side_compact_mentions_inspect() -> None:
    from app.core.agentic_kernel.companion.models import PromptBundle

    text = build_system_prompt(
        PromptBundle(
            identity="i",
            soul="s",
            user_md="u",
            memory_md="m",
        ),
        ContextMeta(),
        enable_user_profile_tool=True,
        tool_side_compact=True,
    )
    assert "companion_runtime_inspect" in text


def test_run_turn_foreground_dual_llm_sets_runtime_inspect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tools run only in tool_background; foreground ``run_turn`` completes dual-LLM chat."""
    from app.core.agentic_kernel.companion.turn import run_turn

    root = tmp_path
    store = get_memory_store(root)
    store.write_document("context.json", '{"context_mode": "intimate"}\n')
    store.write_document("IDENTITY.md", "id\n")
    store.write_document("SOUL.md", "s\n")
    store.write_document("USER.md", "u\n")
    store.write_document("MEMORY.md", "m\n")
    store.write_document("transcript.jsonl", "")

    client = CompanionLLMClient(
        CompanionLLMConfig(
            api_key="secret-key",
            default_model="snap/model",
        )
    )

    env = {
        "user_facing_reply": "final assistant",
        "importance_round": 1,
        "importance_user_message": 1,
        "importance_assistant_message": 1,
    }
    msg = MagicMock()
    msg.content = json.dumps(env)
    msg.tool_calls = []
    ch = MagicMock()
    ch.message = msg
    r = MagicMock()
    r.choices = [ch]

    from app.core.agentic_kernel.companion import turn as turn_mod

    monkeypatch.setattr(turn_mod, "start_tool_background_job", lambda **kwargs: None)

    with patch.object(client, "chat_completion", return_value=r):
        out = asyncio.run(
            run_turn(
                root,
                "user line",
                store=store,
                llm_client=client,
            )
        )
    assert out.assistant_text == "final assistant"
    assert out.tool_background_started is True
