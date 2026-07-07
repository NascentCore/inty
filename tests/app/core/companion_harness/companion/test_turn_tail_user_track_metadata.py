"""JSONL metadata for track-derived tail user transcript rows."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.core.companion_harness.companion.models import CompanionTurnTrack
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.turn_tail_user import (
    TurnTailUserMessage,
    append_turn_track_tail_user_transcript_rows,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    TRANSCRIPT_INNER_TICK_JSONL_REL,
    TRANSCRIPT_JSONL_REL,
)

_TS = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
_TRACE_ID = "trace-test-1"


def _store(tmp_path: Path) -> MemoryStore:
    scope = CompanionScope("tail-meta", "agent-1", tmp_path.name)
    return MemoryStore(scope=scope, repository=None)


def _tail(
    *,
    message_id: str = "user-msg-1",
    text: str = "hello",
) -> tuple[TurnTailUserMessage, ...]:
    return (
        TurnTailUserMessage(
            message_id=message_id,
            text=text,
            received_at_utc=_TS,
        ),
    )


def _transcript_rows(
    store: MemoryStore,
    *,
    rel: str = TRANSCRIPT_JSONL_REL,
) -> list[dict[str, Any]]:
    raw = store.read_document(rel).strip()
    if not raw:
        return []
    return [json.loads(line) for line in raw.splitlines()]


@pytest.mark.parametrize(
    "track, expect_inner_tick, expect_proactive, expect_scheduled",
    [
        (
            CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT,
            True,
            True,
            False,
        ),
        (
            CompanionTurnTrack.INNER_TICK_SCHEDULED,
            True,
            False,
            True,
        ),
        (
            CompanionTurnTrack.INNER_TICK_MONOLOG,
            True,
            False,
            False,
        ),
        (
            CompanionTurnTrack.INNER_TICK_AUTONOMY,
            True,
            False,
            False,
        ),
    ],
)
def test_inner_tick_track_writes_expected_jsonl_flags(
    tmp_path: Path,
    track: CompanionTurnTrack,
    expect_inner_tick: bool,
    expect_proactive: bool,
    expect_scheduled: bool,
) -> None:
    store = _store(tmp_path)
    append_turn_track_tail_user_transcript_rows(
        store,
        TRANSCRIPT_JSONL_REL,
        tail_user_messages=_tail(),
        trace_id=_TRACE_ID,
        track=track,
    )
    rows = _transcript_rows(store)
    assert len(rows) == 1
    row = rows[0]
    assert row["role"] == "user"
    assert row["uuid"] == "user-msg-1"
    assert row["trace_id"] == _TRACE_ID
    assert row.get("inner_tick") is expect_inner_tick
    assert ("proactive_chat" in row) is expect_proactive
    if expect_proactive:
        assert row["proactive_chat"] is True
    assert ("scheduled" in row) is expect_scheduled
    if expect_scheduled:
        assert row["scheduled"] is True


def test_user_chat_track_writes_plain_row(tmp_path: Path) -> None:
    store = _store(tmp_path)
    append_turn_track_tail_user_transcript_rows(
        store,
        TRANSCRIPT_JSONL_REL,
        tail_user_messages=_tail(),
        trace_id=_TRACE_ID,
        track=CompanionTurnTrack.USER_CHAT,
    )
    rows = _transcript_rows(store)
    assert len(rows) == 1
    row = rows[0]
    assert row["role"] == "user"
    assert "inner_tick" not in row
    assert "proactive_chat" not in row
    assert "scheduled" not in row


def test_monolog_track_writes_inner_tick_only_to_inner_tick_jsonl(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    append_turn_track_tail_user_transcript_rows(
        store,
        TRANSCRIPT_INNER_TICK_JSONL_REL,
        tail_user_messages=_tail(),
        trace_id=_TRACE_ID,
        track=CompanionTurnTrack.INNER_TICK_MONOLOG,
    )
    with pytest.raises(FileNotFoundError):
        store.read_document(TRANSCRIPT_JSONL_REL)
    rows = _transcript_rows(store, rel=TRANSCRIPT_INNER_TICK_JSONL_REL)
    assert len(rows) == 1
    assert rows[0].get("inner_tick") is True
    assert "proactive_chat" not in rows[0]
    assert "scheduled" not in rows[0]


def test_multi_message_batch_writes_plain_rows_without_metadata(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    tail = (
        TurnTailUserMessage(
            message_id="user-msg-1",
            text="first",
            received_at_utc=_TS,
        ),
        TurnTailUserMessage(
            message_id="user-msg-2",
            text="second",
            received_at_utc=_TS,
        ),
    )
    append_turn_track_tail_user_transcript_rows(
        store,
        TRANSCRIPT_JSONL_REL,
        tail_user_messages=tail,
        trace_id=_TRACE_ID,
        track=CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT,
    )
    rows = _transcript_rows(store)
    assert len(rows) == 2
    for row in rows:
        assert row["role"] == "user"
        assert "inner_tick" not in row
        assert "proactive_chat" not in row
        assert "scheduled" not in row
