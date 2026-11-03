"""Smoke tests: kernel transcript/context reads use MemoryStoreScopePaths (#3413).

Generated entirely by Cursor agent.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.core.companion_harness.companion.inner_tick_schedule import (
    monolog_transcript_line_count,
)
from app.core.companion_harness.companion.manager import (
    CompanionConfig,
    CompanionManager,
)
from app.core.companion_harness.companion.proactive_chat import (
    ProactiveChatConfig,
    next_proactive_chat_wait_seconds,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_registry import (
    shutdown_all_memory_stores,
)
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)
from app.core.llms.client import CompanionLLMConfig
from tests.app.core.companion_harness.companion_memory_registry_dsn import (
    companion_memory_registry_dsn,
)


def test_monolog_gate_reads_transcript_via_scope_accessor(tmp_path: Path) -> None:
    scope = CompanionScope("kernel-it", "agent-1", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.transcript
    store.append_jsonl_record(
        rel,
        {"role": "user", "content": "hi", "ts": datetime.now(UTC).isoformat()},
    )
    store.append_jsonl_record(
        rel,
        {
            "role": "assistant",
            "content": "hello",
            "ts": datetime.now(UTC).isoformat(),
        },
    )
    assert monolog_transcript_line_count(store) == 2


def test_proactive_chat_scheduling_reads_transcript_via_scope_accessor(
    tmp_path: Path,
) -> None:
    scope = CompanionScope("kernel-pc", "agent-1", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.transcript
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    t1 = t0 + timedelta(seconds=30)
    store.append_jsonl_record(
        rel,
        {"role": "user", "content": "real user", "ts": t0.isoformat()},
    )
    store.append_jsonl_record(
        rel,
        {"role": "assistant", "content": "reply", "ts": t1.isoformat()},
    )
    cfg = ProactiveChatConfig(
        base_idle_sec=10.0,
        min_transcript_lines=2,
        stop_after_silence_minutes=30.0,
    )
    now_past = t1 + timedelta(seconds=120)
    assert next_proactive_chat_wait_seconds(store, cfg, now=now_past) <= 0.0


def test_manager_session_init_writes_context_via_scope_accessor() -> None:
    manager = CompanionManager(
        CompanionConfig(
            llm=CompanionLLMConfig(api_key="test-key"),
            memory_pg_dsn=companion_memory_registry_dsn(),
        )
    )
    session = manager.get_or_create_session("u-scope", "c-scope", "chat-scope")
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.context_json
    raw = session.store.read_document_if_exists(rel)
    assert raw is not None
    assert "context_mode" in raw
    shutdown_all_memory_stores()
