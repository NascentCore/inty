"""Tests for shared transcript assistant JSONL write model (#3407)."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.transcript_assistant_row import (
    TranscriptAssistantRowBuildInput,
    append_transcript_assistant_row,
    build_transcript_assistant_row,
)
from app.core.companion_harness.companion.models import (
    load_transcript_from_store,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)


def test_build_transcript_assistant_row_omits_empty_optionals() -> None:
    row = build_transcript_assistant_row(
        TranscriptAssistantRowBuildInput(
            content="hi",
            uuid="a1",
            reply_to="u1",
            trace_id="t1",
            source="chat",
            significance_perception=None,
            turn_recall=None,
        ),
        ts="2026-06-13T00:00:00+00:00",
    )
    assert row == {
        "role": "assistant",
        "content": "hi",
        "ts": "2026-06-13T00:00:00+00:00",
        "uuid": "a1",
        "reply_to": "u1",
        "source": "chat",
        "trace_id": "t1",
    }


def test_append_transcript_assistant_row_roundtrips_chat_message(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("tar", "a", tmp_path.name),
        repository=None,
    )
    append_transcript_assistant_row(
        store,
        DEFAULT_MEMORY_STORE_SCOPE_PATHS.transcript,
        TranscriptAssistantRowBuildInput(
            content="reply",
            uuid="a1",
            reply_to="u1",
            trace_id="t1",
            source="tool_bg",
            significance_perception={
                "importance_round": 7,
                "importance_user_message": 6,
                "importance_assistant_message": 5,
            },
            turn_recall="用户提到下周见面",
        ),
        ts="2026-06-13T00:00:00+00:00",
    )
    raw = json.loads(
        store.read_document(DEFAULT_MEMORY_STORE_SCOPE_PATHS.transcript).strip()
    )
    assert raw["turn_recall"] == "用户提到下周见面"
    msgs = load_transcript_from_store(
        store,
        DEFAULT_MEMORY_STORE_SCOPE_PATHS.transcript,
    )
    assert len(msgs) == 1
    assert msgs[0].turn_recall == "用户提到下周见面"
    assert msgs[0].significance_perception == {
        "importance_round": 7,
        "importance_user_message": 6,
        "importance_assistant_message": 5,
    }
