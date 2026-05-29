from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.core.companion_harness.companion.maintenance_tick_state import (
    MaintenanceTickState,
    load_maintenance_tick_state,
    save_maintenance_tick_state,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore


def _store(tmp: Path) -> MemoryStore:
    return MemoryStore(
        scope=CompanionScope("mts", "a", tmp.name),
        repository=None,
    )


def test_load_returns_none_when_absent(tmp_path: Path) -> None:
    assert load_maintenance_tick_state(_store(tmp_path)) is None


def test_save_then_load_round_trips_aware_datetime(tmp_path: Path) -> None:
    store = _store(tmp_path)
    now = datetime.now(timezone.utc)
    save_maintenance_tick_state(
        store,
        MaintenanceTickState(
            last_fired_at_utc=now, last_transcript_line_count=7
        ),
    )
    loaded = load_maintenance_tick_state(store)
    assert loaded is not None
    assert loaded.last_transcript_line_count == 7
    assert loaded.last_fired_at_utc == now
    assert loaded.last_fired_at_utc.tzinfo is not None
