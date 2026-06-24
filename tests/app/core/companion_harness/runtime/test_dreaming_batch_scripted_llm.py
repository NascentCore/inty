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
from app.external_services.fakes.openai import fake_step_text
from tests.app.core.companion_harness.companion.companion_scripted_llm import (
    companion_llm_client_with_scripted_transport,
    scripted_harness_llm_config,
)


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
    )

    assert outcome == DreamingBatchOutcome.NOT_DUE
    assert fake.script_index == 0
    assert store.read_document("MEMORY.md") == memory_before
    assert load_dreaming_state(store) == checkpoint
