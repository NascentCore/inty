"""Integrated turn tests for proactive structured output envelope."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any


from app.core.companion_harness.companion.proactive_chat_envelope import (
    PROACTIVE_CHAT_RESPONSE_FORMAT,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.turn import (
    run_companion_inner_tick_proactive_chat_turn,
    run_companion_inner_tick_scheduled_turn,
)
from app.core.companion_harness.companion.turn_deps import CompanionTurnDeps
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.schedule_queue import (
    scheduled_task_synthetic_user_text,
)
from app.core.companion_harness.llm.chat_completions import (
    create_chat_completion_sync,
)
from app.core.llms.client import CompanionLLMConfig
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.utils.models_catalog import GenAIModel, resolve_chat_text_model


def _proactive_envelope_content(*, output_to_user: bool, message: str) -> str:
    return json.dumps(
        {"output_to_user": output_to_user, "message": message},
        ensure_ascii=False,
    )


class _FakeProactiveLLMClient:
    def __init__(self, *, content: str) -> None:
        self.config = CompanionLLMConfig(api_base="https://example.invalid/v1")
        self.calls: list[dict[str, Any]] = []
        self._content = content

    def sync_client_for_route(self, _route: str) -> object:
        return object()

    @property
    def chat_completions_sync(self):
        return create_chat_completion_sync

    def resolve_model(self, role: str) -> GenAIModel:
        return resolve_chat_text_model(f"test/{role}")

    def chat_completion(self, **kwargs: Any) -> Any:
        rec = dict(kwargs)
        if isinstance(rec.get("messages"), list):
            rec["messages"] = list(rec["messages"])
        self.calls.append(rec)
        msg = SimpleNamespace(content=self._content, tool_calls=[])
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    def complete_text(
        self, messages: list[dict[str, Any]], *, model_role: str = "memory"
    ) -> str:
        return ""


def _seed_workspace(store: MemoryStore) -> None:
    store.write_document("IDENTITY.md", "identity")
    store.write_document("SOUL.md", "soul")
    store.write_document("USER.md", "user")
    store.write_document("MEMORY.md", "memory")


def _default_deps(
    store: MemoryStore, client: _FakeProactiveLLMClient
) -> CompanionTurnDeps:
    return CompanionTurnDeps(
        store=store,
        llm_client=client,  # type: ignore[arg-type]
        transcript_compaction=None,
        transcript_llm_window_max_messages=None,
        repository_only_store_text=False,
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        ),
        background_output_sink=None,
        preset_user_msg_uuid=None,
        langsmith_parent_run_enabled=False,
        tool_bg_idle_event=None,
        bootstrap_interim_output_sink=None,
    )


def _transcript_rows(store: MemoryStore) -> list[dict[str, Any]]:
    raw = store.read_document("transcript.jsonl").strip()
    if not raw:
        return []
    return [json.loads(line) for line in raw.splitlines()]


def test_proactive_structured_passes_response_format_kwarg(
    tmp_path: Path,
) -> None:
    content = _proactive_envelope_content(
        output_to_user=False,
        message="",
    )
    scope = CompanionScope("pro-fmt", "a", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    _seed_workspace(store)
    client = _FakeProactiveLLMClient(content=content)

    asyncio.run(
        run_companion_inner_tick_proactive_chat_turn(
            deps=_default_deps(store, client),
        )
    )

    assert client.calls[0]["response_format"] == PROACTIVE_CHAT_RESPONSE_FORMAT


def test_proactive_structured_output_to_user_false_is_silent(
    tmp_path: Path,
) -> None:
    content = _proactive_envelope_content(output_to_user=False, message="")
    scope = CompanionScope("pro-silent", "a", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    _seed_workspace(store)
    client = _FakeProactiveLLMClient(content=content)

    out = asyncio.run(
        run_companion_inner_tick_proactive_chat_turn(
            deps=_default_deps(store, client),
        )
    )

    assert out.assistant_text == ""
    roles = [row["role"] for row in _transcript_rows(store)]
    assert roles.count("user") == 1
    assert "assistant" not in roles


def test_proactive_structured_output_to_user_true_delivers_message(
    tmp_path: Path,
) -> None:
    content = _proactive_envelope_content(
        output_to_user=True,
        message="hey",
    )
    scope = CompanionScope("pro-visible", "a", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    _seed_workspace(store)
    client = _FakeProactiveLLMClient(content=content)

    out = asyncio.run(
        run_companion_inner_tick_proactive_chat_turn(
            deps=_default_deps(store, client),
        )
    )

    assert out.assistant_text == "hey"
    rows = _transcript_rows(store)
    assert rows[-1]["role"] == "assistant"
    assert rows[-1]["content"] == "hey"


def test_proactive_structured_unparseable_body_fail_closed(
    tmp_path: Path,
) -> None:
    scope = CompanionScope("pro-fail", "a", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    _seed_workspace(store)
    client = _FakeProactiveLLMClient(content="not json")

    out = asyncio.run(
        run_companion_inner_tick_proactive_chat_turn(
            deps=_default_deps(store, client),
        )
    )

    assert out.assistant_text == ""
    assert "assistant" not in [row["role"] for row in _transcript_rows(store)]


def test_scheduled_inner_tick_uses_proactive_structured_envelope(
    tmp_path: Path,
) -> None:
    content = _proactive_envelope_content(
        output_to_user=True,
        message="reminder line",
    )
    scope = CompanionScope("sched-env", "a", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    _seed_workspace(store)
    client = _FakeProactiveLLMClient(content=content)
    scheduled_text = scheduled_task_synthetic_user_text(
        task_text="喝水",
        exec_time_utc="2026-05-19T08:00:00Z",
    )

    out = asyncio.run(
        run_companion_inner_tick_scheduled_turn(
            scheduled_text,
            deps=_default_deps(store, client),
        )
    )

    assert out.assistant_text == "reminder line"
    assert client.calls[0]["response_format"] == PROACTIVE_CHAT_RESPONSE_FORMAT
