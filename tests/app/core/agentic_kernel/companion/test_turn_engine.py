from __future__ import annotations

import json
from pathlib import Path

from app.core.agentic_kernel.companion.memory_registry import get_memory_store
from app.core.agentic_kernel.companion.turn_engine import persist_repl_turn_transcript_rows


def test_persist_repl_turn_transcript_rows_writes_jsonl(tmp_path: Path) -> None:
    root = tmp_path
    root.mkdir(parents=True, exist_ok=True)
    get_memory_store(root)
    aid = persist_repl_turn_transcript_rows(
        root,
        user_text="hello",
        assistant_text="hi",
        ts_user="2026-01-01T00:00:00+00:00",
        user_msg_uuid="uu1",
        assistant_reply_to="uu1",
        trace_id="tr1",
    )
    assert aid
    body = get_memory_store(root).read_document("transcript.jsonl")
    lines = body.strip().splitlines()
    assert len(lines) == 2
    u = json.loads(lines[0])
    a = json.loads(lines[1])
    assert u["role"] == "user" and u["uuid"] == "uu1" and u["trace_id"] == "tr1"
    assert a["role"] == "assistant" and a["reply_to"] == "uu1" and a["uuid"] == aid


def test_persist_repl_turn_transcript_rows_assistant_extra(tmp_path: Path) -> None:
    root = tmp_path
    root.mkdir(parents=True, exist_ok=True)
    get_memory_store(root)
    aid = persist_repl_turn_transcript_rows(
        root,
        user_text="hello",
        assistant_text="hi",
        ts_user="2026-01-01T00:00:00+00:00",
        user_msg_uuid="uu1",
        assistant_reply_to="uu1",
        trace_id="tr1",
        assistant_extra={"importance_round": 7},
    )
    body = get_memory_store(root).read_document("transcript.jsonl")
    a = json.loads(body.strip().splitlines()[1])
    assert a.get("significance_perception") == {"importance_round": 7}


def test_persist_repl_maintenance_inner_tick_writes_inner_transcript(tmp_path: Path) -> None:
    root = tmp_path
    root.mkdir(parents=True, exist_ok=True)
    get_memory_store(root)
    persist_repl_turn_transcript_rows(
        root,
        user_text="（内在节拍）",
        assistant_text="internal",
        ts_user="2026-01-01T00:00:00+00:00",
        user_msg_uuid="uu-inner",
        assistant_reply_to="uu-inner",
        inner_tick_turn=True,
        inner_tick_proactive_chat=False,
        assistant_source="inner_tick",
    )
    body = get_memory_store(root).read_document("transcript_inner_tick.jsonl")
    lines = body.strip().splitlines()
    assert len(lines) == 2
