from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from langsmith import tracing_context

from app.core.companion_harness.tools import runtime_inspect_context as ric
from app.core.companion_harness.companion.llm_chat_runtime import tool_path_chat_completion_kwargs
from app.core.companion_harness.companion.llm_client import CompanionLLMClient, CompanionLLMConfig
from app.core.companion_harness.memory.memory_pipeline import MemoryPipelineConfig
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.companion.models import (
    ContextMeta,
    InnerTickMode,
    PromptBundle,
)
from app.core.companion_harness.tools.runtime_inspect_context import (
    build_last_chat_completion_request_payload,
    build_turn_runtime_config_dict,
    runtime_inspect_begin_turn,
    runtime_inspect_end_turn,
    runtime_inspect_set_correlation,
    runtime_inspect_set_last_chat_completion_request,
    runtime_inspect_set_runtime_config,
    runtime_inspect_set_scoped_memory_store,
)
from app.core.companion_harness.companion.runtime_events import append_runtime_event
from app.core.companion_harness.tools.companion_tool_runtime import (
    MEMORY_STORE_READ_DOCUMENT_MAX_CHARS_CAP,
    execute_tool_call,
)
from app.core.companion_harness.tools.runtime_inspect_tool import tool_companion_runtime_inspect
from app.core.companion_harness.companion.prompt_slices import (
    SYSTEM_PROMPT_SLICE_SEPARATOR,
)
from app.core.companion_harness.companion.prompts.system_messages import (
    build_system_messages,
)


def _concatenated_system_text(
    bundle: PromptBundle,
    context: ContextMeta,
    **kwargs: Any,
) -> str:
    msgs = build_system_messages(bundle, context, **kwargs)
    return SYSTEM_PROMPT_SLICE_SEPARATOR.join(
        str(m.get("content") or "") for m in msgs
    )


from app.core.companion_harness.companion.scope import CompanionScope
from app.utils.models_catalog import resolve_chat_text_model


_LANGSMITH_TEST_PROJECT = "inty-backend-test-runtime-inspect"


@pytest.fixture(autouse=True)
def _isolate_langsmith_test_project(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    monkeypatch.setenv("LANGSMITH_PROJECT", _LANGSMITH_TEST_PROJECT)
    monkeypatch.setenv("LANGCHAIN_PROJECT", _LANGSMITH_TEST_PROJECT)
    with tracing_context(project_name=_LANGSMITH_TEST_PROJECT):
        yield


@pytest.fixture(autouse=True)
def _debug_runtime_inspect_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("INTY_RUNTIME_MODE", "DEBUG")
    monkeypatch.setenv("INTY_OPS_WORKSPACE", str(tmp_path))


def _run_tool(store, name: str, args: str) -> str:
    return asyncio.run(execute_tool_call(store, name, args))


class _DualLlmForegroundStubCompanionLLMClient(CompanionLLMClient):
    """Returns a fixed dual-LLM envelope without HTTP or MagicMock."""

    def __init__(self, envelope_json: str, config: CompanionLLMConfig) -> None:
        super().__init__(config)
        self._envelope_json = envelope_json

    def chat_completion(
        self,
        *,
        messages: list[dict[str, Any]],
        model: Any | None = None,
        tools: list[Any] | None = None,
        tool_choice: str | None = None,
        response_format: dict[str, Any] | None = None,
        scene: Any | None = None,
        langsmith_extra: dict[str, Any] | None = None,
        high_reasoning: bool = False,
    ) -> Any:
        message = SimpleNamespace(
            content=self._envelope_json,
            tool_calls=[],
            reasoning=None,
            reasoning_details=None,
        )
        choice = SimpleNamespace(message=message)
        return SimpleNamespace(choices=[choice])


def test_companion_runtime_inspect_outside_scope(tmp_path: Path) -> None:
    scope = CompanionScope("ri", "a", f"out-{tmp_path.name}")
    store = MemoryStore(scope=scope, repository=None)
    out = _run_tool(store, "companion_runtime_inspect", "{}")
    data = json.loads(out)
    assert "runtime_unavailable_reason" in data
    assert data["runtime_config"] is None
    assert data["last_chat_completion_request"] is None
    assert "correlation" not in data


def test_companion_runtime_inspect_with_contextvar(tmp_path: Path) -> None:
    scope = CompanionScope("ri", "a", f"ctx-{tmp_path.name}")
    store = MemoryStore(scope=scope, repository=None)
    store.write_document("SOUL.md", "soul-content-here")
    append_runtime_event(
        store,
        {"ts": "2026-05-08T00:00:00Z", "kind": "tool_timeout", "detail": "slow"},
    )
    token = runtime_inspect_begin_turn()
    try:
        runtime_inspect_set_scoped_memory_store(store)
        client = CompanionLLMClient(
            CompanionLLMConfig(
                api_key="super-secret-key",
                default_model=resolve_chat_text_model("test/model-a"),
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
                repository_only_store_text=True,
                transcript_compaction=None,
                memory_store_read_document_max_chars_cap=(
                    MEMORY_STORE_READ_DOCUMENT_MAX_CHARS_CAP
                ),
            )
        )
        runtime_inspect_set_last_chat_completion_request(
            build_last_chat_completion_request_payload(
                model=resolve_chat_text_model("test/model-a"),
                messages=[
                    {"role": "system", "content": "system text"},
                    {"role": "user", "content": "hello"},
                ],
                tools=None,
            )
        )
        runtime_inspect_set_correlation(
            {"trace_id": "trace-test-1", "user_msg_uuid": "user-msg-test-1"}
        )
        json.dumps(ric.runtime_inspect_get_bundle())
        out = _run_tool(store, "companion_runtime_inspect", "{}")
        data = json.loads(out)
        assert data["runtime_config"]["llm"]["api_key"] == "***"
        assert "super-secret-key" not in out
        assert data["last_chat_completion_request"]["model"] == "test/model-a"
        msgs = data["last_chat_completion_request"]["messages"]
        assert msgs[0]["role"] == "system"
        assert msgs[1]["content"] == "hello"
        assert (
            data["last_chat_completion_request"]["openrouter_extra_body"]
            == tool_path_chat_completion_kwargs(
                resolve_chat_text_model("test/model-a")
            )
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
        assert data["correlation"] == {
            "trace_id": "trace-test-1",
            "user_msg_uuid": "user-msg-test-1",
        }
    finally:
        runtime_inspect_end_turn(token)


def test_companion_runtime_inspect_thread_overlay(tmp_path: Path) -> None:
    scope = CompanionScope("ri", "a", f"ov-{tmp_path.name}")
    scoped = MemoryStore(scope=scope, repository=None)
    ric.runtime_inspect_thread_overlay_begin(
        {
            "runtime_config": {"source": "tool_background", "tool_model_name": "bg/model"},
            "last_chat_completion_request": None,
            "scoped_memory_store": scoped,
            "correlation": {
                "trace_id": "bg-trace",
                "user_msg_uuid": "bg-user-uuid",
            },
        }
    )
    try:
        ric.runtime_inspect_set_last_chat_completion_request(
            build_last_chat_completion_request_payload(
                model=resolve_chat_text_model("bg/model"),
                messages=[{"role": "user", "content": "bg-user"}],
                tools=[],
            )
        )
        out = tool_companion_runtime_inspect(scoped, {"include_store_documents": False})
        data = json.loads(out)
        assert data["runtime_config"]["source"] == "tool_background"
        assert data["last_chat_completion_request"]["messages"][-1]["content"] == "bg-user"
        assert data["correlation"] == {
            "trace_id": "bg-trace",
            "user_msg_uuid": "bg-user-uuid",
        }
        assert "store_documents" not in data
    finally:
        ric.runtime_inspect_thread_overlay_end()


def test_companion_runtime_inspect_prefers_scoped_memory_store(tmp_path: Path) -> None:
    scope_default = CompanionScope("u-d", "a", f"def-{tmp_path.name}")
    scope_scoped = CompanionScope("u-s", "a", f"scoped-{tmp_path.name}")
    store_scoped = MemoryStore(scope=scope_scoped, repository=None)
    store_scoped.write_document("SOUL.md", "scoped-soul-body")
    store_default = MemoryStore(scope=scope_default, repository=None)
    assert store_default is not store_scoped
    token = runtime_inspect_begin_turn()
    try:
        runtime_inspect_set_scoped_memory_store(store_scoped)
        out = tool_companion_runtime_inspect(store_default, {})
        data = json.loads(out)
        assert "scoped-soul-body" in data["store_documents"]["SOUL.md"]["text"]
    finally:
        runtime_inspect_end_turn(token)


def test_runtime_inspect_writes_zip(tmp_path: Path) -> None:
    scope = CompanionScope("ri", "a", f"zip-{tmp_path.name}")
    store = MemoryStore(scope=scope, repository=None)
    store.write_document("SOUL.md", "zip-soul")
    token = runtime_inspect_begin_turn()
    try:
        runtime_inspect_set_scoped_memory_store(store)
        runtime_inspect_set_correlation(
            {"trace_id": "t-zip", "user_msg_uuid": "u-zip-test"}
        )
        out = tool_companion_runtime_inspect(store, {})
        data = json.loads(out)
        zip_abs = data["export_zip_absolute_path"]
        zip_rel = data["export_zip_repo_relative_path"]
        assert zip_abs
        assert zip_rel
        zip_path = Path(zip_abs)
        assert zip_path.is_file()
        assert zip_path.suffix == ".zip"
        import zipfile

        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
        assert "inspect_snapshot.json" in names
        assert "manifest.json" in names
    finally:
        runtime_inspect_end_turn(token)


def test_system_prompt_prod_no_inspect(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTY_RUNTIME_MODE", "PROD")
    text = _concatenated_system_text(
        PromptBundle(
            identity="i",
            soul="s",
            user_md="u",
            memory_md="m",
        ),
        ContextMeta(),
        enable_tools=True,
    )
    assert "companion_runtime_inspect" not in text


def test_build_system_prompt_tools_contract_mentions_inspect() -> None:
    from app.core.companion_harness.companion.models import PromptBundle

    text = _concatenated_system_text(
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
    from app.core.companion_harness.companion.models import PromptBundle

    text = _concatenated_system_text(
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
    from app.core.companion_harness.companion.turn import run_turn

    scope = CompanionScope("ri", "a", f"dual-{tmp_path.name}")
    store = MemoryStore(scope=scope, repository=None)
    store.write_document("context.json", '{"context_mode": "intimate"}\n')
    store.write_document("IDENTITY.md", "id\n")
    store.write_document("SOUL.md", "s\n")
    store.write_document("USER.md", "u\n")
    store.write_document("MEMORY.md", "m\n")
    store.write_document("transcript.jsonl", "")

    envelope = {
        "user_facing_reply": "final assistant",
        "importance_round": 1,
        "importance_user_message": 1,
        "importance_assistant_message": 1,
        "output_to_user": True,
    }
    client = _DualLlmForegroundStubCompanionLLMClient(
        json.dumps(envelope),
        CompanionLLMConfig(
            api_key="secret-key",
            default_model=resolve_chat_text_model("snap/model"),
        ),
    )

    from app.core.companion_harness.companion import turn as turn_mod

    monkeypatch.setattr(
        turn_mod, "start_tool_background_job", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        turn_mod, "schedule_memory_update_after_turn", lambda *args, **kwargs: None
    )

    out = asyncio.run(
        run_turn(
            "user line",
            store=store,
            llm_client=client,
            langsmith_parent_run_enabled=False,
        )
    )
    assert out.assistant_text == "final assistant"
    assert out.tool_background_started is True
