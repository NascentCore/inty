"""tool_background transcript rows carry finish-envelope metadata."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    TRANSCRIPT_JSONL_REL,
)
from app.core.companion_harness.tools.tool_background import (
    _append_background_transcript_assistant,
)


def test_append_background_transcript_assistant_persists_turn_recall(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("tbg-meta", "agent", str(tmp_path.resolve())),
        repository=None,
    )
    _append_background_transcript_assistant(
        store=store,
        content="done",
        assistant_msg_uuid="a-1",
        reply_to="u-1",
        trace_id="trace-1",
        transcript_relative_path=TRANSCRIPT_JSONL_REL,
        significance_perception={"importance_round": 6},
        turn_recall="用户提到下周见面",
    )
    row = json.loads(store.read_document(TRANSCRIPT_JSONL_REL).strip())
    assert row["turn_recall"] == "用户提到下周见面"
    assert row["significance_perception"] == {"importance_round": 6}
