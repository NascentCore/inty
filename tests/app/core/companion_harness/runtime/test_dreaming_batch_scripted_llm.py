"""Integration tests for DreamingBatch with scripted FakeOpenAI transport.

Generated entirely by Cursor agent.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.core.companion_harness.companion.dreaming import (
    DreamingState,
    load_dreaming_state,
    save_dreaming_state,
)
from app.core.companion_harness.companion.dreaming_observability import (
    DreamingBatchOutcome,
)
from app.core.companion_harness.companion.manager import (
    CompanionConfig,
    CompanionSession,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.runtime.dreaming_batch import (
    run_dreaming_batch_if_due,
)
from app.external_services.fakes.openai import (
    fake_step_text,
    fake_step_tool_calls,
)
from app.utils.config import DreamingCuratorMode
from tests.app.core.companion_harness.companion.companion_scripted_llm import (
    companion_llm_client_with_scripted_transport,
    scripted_harness_llm_config,
)

_DREAMING_UPDATE_TOOL = "update_dreaming_document"


def _memory_store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(
        scope=CompanionScope("dream-skip", "agent", tmp_path.name),
        repository=None,
    )


def _seed_settled_scope_with_checkpoint(
    store: MemoryStore,
) -> DreamingState:
    """Bootstrap-complete scope whose transcript ends at a dreaming checkpoint."""
    now = datetime.now(UTC)
    user_ts = now - timedelta(days=2, hours=1)
    assistant_ts = user_ts + timedelta(minutes=1)
    checkpoint_at = now - timedelta(days=1)

    store.write_document(
        "context.json",
        json.dumps(
            {
                "context_mode": "public",
                "user_id": "dream-skip",
                "companion_id": "agent",
                "chat_id": store.scope.chat_id,
                "workspace_bootstrap_user_interactive_completed": True,
            },
            ensure_ascii=False,
        )
        + "\n",
    )
    for rel in ("IDENTITY.md", "SOUL.md", "USER.md", "MEMORY.md"):
        store.write_document(rel, f"# {rel}\n")

    store.write_document(
        "transcript.jsonl",
        "\n".join(
            [
                json.dumps(
                    {
                        "role": "user",
                        "content": "hello before dream",
                        "ts": user_ts.isoformat(),
                        "uuid": "user-before-dream",
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "role": "assistant",
                        "content": "reply before dream",
                        "ts": assistant_ts.isoformat(),
                        "uuid": "asst-before-dream",
                        "reply_to": "user-before-dream",
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "role": "assistant",
                        "content": "proactive only after checkpoint",
                        "ts": (checkpoint_at + timedelta(hours=1)).isoformat(),
                        "uuid": "asst-proactive-after-dream",
                        "proactive_chat": True,
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
    )

    state = DreamingState(
        last_processed_main_line_count=2,
        last_processed_main_uuid="asst-before-dream",
        last_processed_at=checkpoint_at,
        last_processed_latest_user_ts=user_ts,
        last_processed_calendar_date=checkpoint_at,
    )
    save_dreaming_state(store, state)
    return state


def _companion_session(store: MemoryStore, llm_client) -> CompanionSession:
    scope = store.scope
    config = CompanionConfig(
        llm=scripted_harness_llm_config(),
        memory_pg_dsn="",
        langsmith_companion_parent_run_enabled=False,
    )
    return CompanionSession(
        scope=scope,
        store=store,
        llm_client=llm_client,
        config=config,
    )


def test_run_dreaming_batch_if_due_skips_without_llm_when_no_user_messages_since_checkpoint(
    tmp_path: Path,
) -> None:
    """DreamingBatch must not call LLM when no real user rows exist after checkpoint."""
    store = _memory_store(tmp_path)
    checkpoint = _seed_settled_scope_with_checkpoint(store)
    memory_before = store.read_document("MEMORY.md")

    llm_config = scripted_harness_llm_config()
    client, fake = companion_llm_client_with_scripted_transport(
        llm_config,
        (fake_step_text("dreaming must not run"),),
    )
    session = _companion_session(store, client)
    assert session.is_initialized is True

    outcome = run_dreaming_batch_if_due(
        session,
        idle_seconds=1,
        curator_mode=DreamingCuratorMode.SEQUENTIAL,
    )

    assert outcome == DreamingBatchOutcome.NOT_DUE
    assert fake.script_index == 0
    assert store.read_document("MEMORY.md") == memory_before
    assert load_dreaming_state(store) == checkpoint


def _seed_scope_due_for_one_shot_dreaming(store: MemoryStore) -> str:
    """Bootstrap-complete scope with one idle user turn and no checkpoint."""
    now = datetime.now(UTC)
    user_ts = now - timedelta(hours=3)
    assistant_ts = user_ts + timedelta(minutes=1)
    day_iso = user_ts.date().isoformat()
    daily_path = f"memory/daily/{day_iso}.md"

    store.write_document(
        "context.json",
        json.dumps(
            {
                "context_mode": "public",
                "user_id": store.scope.user_id,
                "companion_id": store.scope.companion_id,
                "chat_id": store.scope.chat_id,
                "workspace_bootstrap_user_interactive_completed": True,
            },
            ensure_ascii=False,
        )
        + "\n",
    )
    for rel in (
        "IDENTITY.md",
        "SOUL.md",
        "USER.md",
        "MEMORY.md",
        "STYLE.md",
        "COMPANIONSHIP.md",
    ):
        store.write_document(rel, f"# {rel}\n")

    store.write_document(
        "transcript.jsonl",
        "\n".join(
            [
                json.dumps(
                    {
                        "role": "user",
                        "content": "dreaming slice user",
                        "ts": user_ts.isoformat(),
                        "uuid": "user-dream-due",
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "role": "assistant",
                        "content": "dreaming slice assistant",
                        "ts": assistant_ts.isoformat(),
                        "uuid": "asst-dream-due",
                        "reply_to": "user-dream-due",
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
    )
    return daily_path


def _one_shot_dreaming_script_step(daily_path: str) -> tuple:
    paths = (
        daily_path,
        "MEMORY.md",
        "USER.md",
        "STYLE.md",
        "SOUL.md",
        "COMPANIONSHIP.md",
    )
    calls: list[tuple[str, str, str]] = []
    for rel in paths:
        if rel.startswith("memory/daily/"):
            kind = "daily_gist"
        elif rel == "MEMORY.md":
            kind = "memory"
        elif rel == "USER.md":
            kind = "user"
        elif rel == "STYLE.md":
            kind = "style"
        elif rel == "SOUL.md":
            kind = "soul"
        else:
            kind = "companionship"
        payload = json.dumps(
            {
                "document_kind": kind,
                "relative_path": rel,
                "content_changed": True,
                "body": f"{rel} scripted",
                "changed_reason": "scripted test",
            },
            ensure_ascii=False,
        )
        calls.append((_DREAMING_UPDATE_TOOL, payload, f"tc-{rel}"))
    return (fake_step_tool_calls(*calls),)


def test_run_dreaming_batch_if_due_one_shot_uses_single_llm_and_saves_checkpoint(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("dream-one-shot", "agent", tmp_path.name),
        repository=None,
    )
    daily_path = _seed_scope_due_for_one_shot_dreaming(store)
    assert load_dreaming_state(store) is None

    llm_config = scripted_harness_llm_config()
    client, fake = companion_llm_client_with_scripted_transport(
        llm_config,
        _one_shot_dreaming_script_step(daily_path),
    )
    session = _companion_session(store, client)

    outcome = run_dreaming_batch_if_due(
        session,
        idle_seconds=1,
        curator_mode=DreamingCuratorMode.ONE_SHOT,
    )

    assert outcome == DreamingBatchOutcome.CHECKPOINT_SAVED
    assert fake.script_index == 1
    assert store.read_document(daily_path) == f"{daily_path} scripted\n"
    assert store.read_document("MEMORY.md") == "MEMORY.md scripted\n"
    assert load_dreaming_state(store) is not None
