from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.companion_harness.companion.models import (
    ChatMessage,
    CompanionTurnTrack,
    companion_turn_transcript_loaded_messages,
    merge_transcripts_by_ts,
    transcript_relative_path_for_turn_persistence,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)

_PATHS = DEFAULT_MEMORY_STORE_SCOPE_PATHS


def test_merge_transcripts_by_ts_orders_then_stable_tiebreak() -> None:
    main = [
        ChatMessage(role="user", content="a", ts="2026-05-01T00:00:02Z"),
    ]
    inner = [
        ChatMessage(role="user", content="b", ts="2026-05-01T00:00:02Z"),
    ]
    merged = merge_transcripts_by_ts(main, inner)
    assert [m.content for m in merged] == ["a", "b"]


@pytest.mark.parametrize(
    "track, expected_rel",
    [
        (CompanionTurnTrack.USER_CHAT, _PATHS.transcript),
        (CompanionTurnTrack.USER_CHAT_BOOTSTRAP, _PATHS.transcript),
        (CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING, _PATHS.transcript),
        (CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT, _PATHS.transcript),
        (CompanionTurnTrack.INNER_TICK_SCHEDULED, _PATHS.transcript),
        (
            CompanionTurnTrack.INNER_TICK_MONOLOG,
            _PATHS.transcript_inner_tick,
        ),
        (
            CompanionTurnTrack.INNER_TICK_AUTONOMY,
            _PATHS.transcript_inner_tick,
        ),
    ],
)
def test_transcript_relative_path_for_turn_persistence_by_track(
    track: CompanionTurnTrack,
    expected_rel: str,
) -> None:
    assert (
        transcript_relative_path_for_turn_persistence(track=track)
        == expected_rel
    )


def _store(tmp_path: Path) -> MemoryStore:
    scope = CompanionScope("load-policy", "agent-1", tmp_path.name)
    return MemoryStore(scope=scope, repository=None)


def _seed_transcripts(store: MemoryStore) -> None:
    main_row = {
        "role": "user",
        "content": "main",
        "ts": "2026-05-01T00:00:02Z",
        "uuid": "main-1",
    }
    inner_row = {
        "role": "user",
        "content": "inner",
        "ts": "2026-05-01T00:00:03Z",
        "uuid": "inner-1",
    }
    store.write_document(
        _PATHS.transcript,
        json.dumps(main_row, ensure_ascii=False) + "\n",
    )
    store.write_document(
        _PATHS.transcript_inner_tick,
        json.dumps(inner_row, ensure_ascii=False) + "\n",
    )


def _loaded_contents(
    store: MemoryStore,
    *,
    track: CompanionTurnTrack,
) -> list[str]:
    loaded = companion_turn_transcript_loaded_messages(
        store,
        rel_main_transcript=_PATHS.transcript,
        rel_inner_tick_transcript=_PATHS.transcript_inner_tick,
        track=track,
    )
    return [row.content for row in loaded]


def test_monolog_track_merges_main_and_inner(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_transcripts(store)
    assert _loaded_contents(
        store, track=CompanionTurnTrack.INNER_TICK_MONOLOG
    ) == ["main", "inner"]


def test_autonomy_track_merges_main_and_inner(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_transcripts(store)
    assert _loaded_contents(
        store, track=CompanionTurnTrack.INNER_TICK_AUTONOMY
    ) == ["main", "inner"]


def test_user_chat_track_loads_main_only(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_transcripts(store)
    assert _loaded_contents(store, track=CompanionTurnTrack.USER_CHAT) == [
        "main"
    ]


def test_proactive_chat_track_loads_main_only(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _seed_transcripts(store)
    assert _loaded_contents(
        store, track=CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT
    ) == ["main"]
