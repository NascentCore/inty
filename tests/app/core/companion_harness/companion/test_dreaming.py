from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from app.core.companion_harness.companion.dreaming import (
    DreamingState,
    apply_dreaming_checkpoint_to_prompt_rows,
    dreaming_candidate_slice,
    dreaming_due,
    load_dreaming_state,
    save_dreaming_state,
)
from app.core.companion_harness.companion.models import ChatMessage
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)


def _store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(
        scope=CompanionScope("dream", "agent", tmp_path.name),
        repository=None,
    )


def _write_transcript(
    store: MemoryStore, rows: list[dict[str, object]]
) -> None:
    body = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n"
    store.write_document(DEFAULT_MEMORY_STORE_SCOPE_PATHS.transcript, body)


def test_dreaming_without_checkpoint_looks_back_24h(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _write_transcript(
        store,
        [
            {
                "role": "user",
                "content": "old",
                "ts": "2026-01-01T10:00:00+00:00",
                "uuid": "old-u",
            },
            {
                "role": "assistant",
                "content": "old reply",
                "ts": "2026-01-01T10:01:00+00:00",
                "uuid": "old-a",
            },
            {
                "role": "user",
                "content": "new",
                "ts": "2026-01-02T11:00:00+00:00",
                "uuid": "new-u",
            },
            {
                "role": "assistant",
                "content": "new reply",
                "ts": "2026-01-02T11:01:00+00:00",
                "uuid": "new-a",
            },
        ],
    )
    candidate = dreaming_candidate_slice(
        store, now=datetime(2026, 1, 2, 12, 0, tzinfo=UTC)
    )
    assert candidate is not None
    assert [row.content for row in candidate.rows] == ["new", "new reply"]
    assert candidate.boundary_uuid == "new-a"


def test_dreaming_due_uses_idle_seconds(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _write_transcript(
        store,
        [
            {
                "role": "user",
                "content": "sleepy",
                "ts": "2026-01-02T09:00:00+00:00",
                "uuid": "u",
            },
            {
                "role": "assistant",
                "content": "rest",
                "ts": "2026-01-02T09:01:00+00:00",
                "uuid": "a",
            },
        ],
    )
    now = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)
    assert dreaming_due(store, now=now, dreaming_idle_seconds=7200) is not None
    assert dreaming_due(store, now=now, dreaming_idle_seconds=14400) is None


def test_dreaming_due_skips_after_same_day_checkpoint(tmp_path: Path) -> None:
    """Same UTC day after a successful dream: no second dream (expected product behavior)."""
    store = _store(tmp_path)
    _write_transcript(
        store,
        [
            {
                "role": "user",
                "content": "morning",
                "ts": "2026-01-02T09:00:00+00:00",
                "uuid": "u1",
            },
            {
                "role": "assistant",
                "content": "morning reply",
                "ts": "2026-01-02T09:01:00+00:00",
                "uuid": "a1",
            },
            {
                "role": "user",
                "content": "evening",
                "ts": "2026-01-02T18:00:00+00:00",
                "uuid": "u2",
            },
            {
                "role": "assistant",
                "content": "evening reply",
                "ts": "2026-01-02T18:01:00+00:00",
                "uuid": "a2",
            },
        ],
    )
    save_dreaming_state(
        store,
        DreamingState(
            last_processed_main_line_count=2,
            last_processed_main_uuid="a1",
            last_processed_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
            last_processed_latest_user_ts=datetime(
                2026, 1, 2, 9, 0, tzinfo=UTC
            ),
            last_processed_calendar_date=datetime(
                2026, 1, 2, 12, 0, tzinfo=UTC
            ),
        ),
    )

    assert (
        dreaming_due(
            store,
            now=datetime(2026, 1, 2, 23, 0, tzinfo=UTC),
            dreaming_idle_seconds=7200,
        )
        is None
    )


def test_dreaming_due_skips_when_no_user_messages_since_checkpoint(
    tmp_path: Path,
) -> None:
    """After checkpoint, only non-user transcript rows must not trigger dreaming."""
    store = _store(tmp_path)
    _write_transcript(
        store,
        [
            {
                "role": "user",
                "content": "morning",
                "ts": "2026-01-02T09:00:00+00:00",
                "uuid": "u1",
            },
            {
                "role": "assistant",
                "content": "morning reply",
                "ts": "2026-01-02T09:01:00+00:00",
                "uuid": "a1",
            },
            {
                "role": "assistant",
                "content": "proactive ping",
                "ts": "2026-01-02T18:00:00+00:00",
                "uuid": "a2",
                "proactive_chat": True,
            },
        ],
    )
    save_dreaming_state(
        store,
        DreamingState(
            last_processed_main_line_count=2,
            last_processed_main_uuid="a1",
            last_processed_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
            last_processed_latest_user_ts=datetime(
                2026, 1, 2, 9, 0, tzinfo=UTC
            ),
            last_processed_calendar_date=datetime(
                2026, 1, 2, 12, 0, tzinfo=UTC
            ),
        ),
    )

    assert (
        dreaming_due(
            store,
            now=datetime(2026, 1, 3, 9, 0, tzinfo=UTC),
            dreaming_idle_seconds=7200,
        )
        is None
    )
    assert (
        dreaming_candidate_slice(
            store, now=datetime(2026, 1, 3, 9, 0, tzinfo=UTC)
        )
        is None
    )


def test_dreaming_due_allows_next_day_after_checkpoint(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _write_transcript(
        store,
        [
            {
                "role": "user",
                "content": "morning",
                "ts": "2026-01-02T09:00:00+00:00",
                "uuid": "u1",
            },
            {
                "role": "assistant",
                "content": "morning reply",
                "ts": "2026-01-02T09:01:00+00:00",
                "uuid": "a1",
            },
            {
                "role": "user",
                "content": "evening",
                "ts": "2026-01-02T18:00:00+00:00",
                "uuid": "u2",
            },
            {
                "role": "assistant",
                "content": "evening reply",
                "ts": "2026-01-02T18:01:00+00:00",
                "uuid": "a2",
            },
        ],
    )
    save_dreaming_state(
        store,
        DreamingState(
            last_processed_main_line_count=2,
            last_processed_main_uuid="a1",
            last_processed_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
            last_processed_latest_user_ts=datetime(
                2026, 1, 2, 9, 0, tzinfo=UTC
            ),
            last_processed_calendar_date=datetime(
                2026, 1, 2, 12, 0, tzinfo=UTC
            ),
        ),
    )

    candidate = dreaming_due(
        store,
        now=datetime(2026, 1, 3, 9, 0, tzinfo=UTC),
        dreaming_idle_seconds=7200,
    )

    assert candidate is not None
    assert [row.content for row in candidate.rows] == [
        "evening",
        "evening reply",
    ]


def test_dreaming_state_roundtrip_uses_datetime(tmp_path: Path) -> None:
    store = _store(tmp_path)
    state = DreamingState(
        last_processed_main_line_count=2,
        last_processed_main_uuid="a",
        last_processed_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
        last_processed_latest_user_ts=datetime(
            2026, 1, 2, 9, 0, tzinfo=UTC
        ),
        last_processed_calendar_date=datetime(
            2026, 1, 2, 0, 0, tzinfo=UTC
        ),
    )
    save_dreaming_state(store, state)
    loaded = load_dreaming_state(store)
    assert loaded == state


def test_apply_dreaming_checkpoint_to_prompt_rows() -> None:
    rows = [
        ChatMessage(
            role="user",
            content="before",
            ts="2026-01-02T09:00:00+00:00",
            uuid="u1",
        ),
        ChatMessage(
            role="assistant",
            content="checkpoint",
            ts="2026-01-02T09:01:00+00:00",
            uuid="a1",
        ),
        ChatMessage(
            role="user",
            content="after",
            ts="2026-01-02T12:00:00+00:00",
            uuid="u2",
        ),
    ]
    state = DreamingState(
        last_processed_main_line_count=2,
        last_processed_main_uuid="a1",
        last_processed_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
        last_processed_latest_user_ts=datetime(
            2026, 1, 2, 9, 0, tzinfo=UTC
        ),
        last_processed_calendar_date=datetime(
            2026, 1, 2, 0, 0, tzinfo=UTC
        ),
    )
    assert apply_dreaming_checkpoint_to_prompt_rows(rows, state) == rows[2:]
