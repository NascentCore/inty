from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from app.core.companion_harness.companion.dreaming import (
    DreamingState,
    save_dreaming_state,
)
from app.core.companion_harness.companion.models import CompanionTurnTrack
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.turn_pipeline import (
    load_companion_turn_state,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    TRANSCRIPT_JSONL_REL,
)
from app.core.companion_harness.memory.memory_store_scope import (
    ensure_minimal_documents_in_store,
)


def test_load_companion_turn_state_applies_dreaming_checkpoint(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("dream-prompt", "agent", tmp_path.name),
        repository=None,
    )
    ensure_minimal_documents_in_store(store)
    rows = [
        {
            "role": "user",
            "content": "before",
            "ts": "2026-01-02T09:00:00+00:00",
            "uuid": "u1",
        },
        {
            "role": "assistant",
            "content": "checkpoint",
            "ts": "2026-01-02T09:01:00+00:00",
            "uuid": "a1",
        },
        {
            "role": "user",
            "content": "after",
            "ts": "2026-01-02T12:00:00+00:00",
            "uuid": "u2",
        },
    ]
    store.write_document(
        TRANSCRIPT_JSONL_REL,
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
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
            last_processed_calendar_date=datetime(2026, 1, 2, 0, 0, tzinfo=UTC),
        ),
    )
    loaded = load_companion_turn_state(
        store=store,
        track=CompanionTurnTrack.USER_CHAT,
        transcript_llm_window_max_messages=None,
    )
    assert [row.content for row in loaded.loaded_transcript] == ["after"]
