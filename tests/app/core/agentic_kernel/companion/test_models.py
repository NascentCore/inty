from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.agentic_kernel.companion.memory_store import MemoryStore
from app.core.agentic_kernel.companion.models import (
    TRANSCRIPT_WINDOW_MAX_MESSAGES,
    ChatMessage,
    ContextMeta,
    PromptBundle,
    load_transcript,
    load_transcript_from_store,
    load_transcript_text,
    transcript_for_llm_turn,
    transcript_without_trailing_presence_signals,
)


def test_chat_message_basic() -> None:
    m = ChatMessage(role="user", content="hello", ts="2026-01-01T00:00:00+00:00")
    assert m.role == "user"
    assert m.content == "hello"
    assert m.ts == "2026-01-01T00:00:00+00:00"


def test_chat_message_timestamp_alias() -> None:
    m = ChatMessage.model_validate(
        {
            "role": "assistant",
            "content": "hi",
            "timestamp": "2026-01-02T12:00:00Z",
        }
    )
    assert m.ts == "2026-01-02T12:00:00Z"


def test_prompt_bundle_defaults() -> None:
    b = PromptBundle(identity="i", soul="s", user_md="u", memory_md="m")
    assert b.tools_md == ""
    assert b.memory_raw_diary_today_md == ""
    assert b.memory_day_summary_today_md == ""


def test_context_meta_defaults() -> None:
    c = ContextMeta()
    assert c.context_mode == "intimate"
    assert c.post_bootstrap_context_mode is None
    assert c.workspace_bootstrap_user_interactive_completed is True
    assert c.companion_ws_session_system_written is True
    assert c.companion_ws_interactive_kickoff_sent is True


def test_context_meta_normalizes_experience_profile_id() -> None:
    c = ContextMeta(context_mode="  PUBLIC ")
    assert c.context_mode == "public"


def test_context_meta_post_bootstrap_context_mode_rejects_bootstrap_value() -> None:
    with pytest.raises(ValueError, match="post_bootstrap_context_mode"):
        ContextMeta(
            context_mode="intimate",
            post_bootstrap_context_mode="bootstrap",
        )


def test_context_meta_accepts_bootstrap_context_mode_with_post_target() -> None:
    c = ContextMeta(
        context_mode="bootstrap",
        post_bootstrap_context_mode="roleplay",
    )
    assert c.context_mode == "bootstrap"
    assert c.post_bootstrap_context_mode == "roleplay"


def test_transcript_for_llm_turn_short() -> None:
    loaded = [
        ChatMessage(role="user", content=str(i), ts=f"2026-01-01T00:{i:02d}:00Z")
        for i in range(19)
    ]
    assert transcript_for_llm_turn(loaded) == loaded


def test_transcript_for_llm_turn_truncate() -> None:
    loaded = [
        ChatMessage(role="user", content=str(i), ts=f"2026-01-01T00:{i:02d}:00Z")
        for i in range(25)
    ]
    out = transcript_for_llm_turn(loaded)
    assert len(out) == TRANSCRIPT_WINDOW_MAX_MESSAGES
    assert out[0].content == str(25 - TRANSCRIPT_WINDOW_MAX_MESSAGES)


def test_transcript_for_llm_turn_custom_window() -> None:
    loaded = [
        ChatMessage(role="user", content=str(i), ts=f"2026-01-01T00:{i:02d}:00Z")
        for i in range(15)
    ]
    out = transcript_for_llm_turn(loaded, max_messages=8)
    assert len(out) == 8
    assert out[0].content == str(15 - 8)


def test_load_transcript_empty_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.jsonl"
    assert load_transcript(missing) == []


def test_load_transcript_text() -> None:
    text = (
        '{"role": "user", "content": "a", "ts": "2026-01-01T00:00:00Z"}\n'
        '{"role": "assistant", "content": "b", "timestamp": "2026-01-01T00:01:00Z"}\n'
    )
    msgs = load_transcript_text(text)
    assert len(msgs) == 2


def test_load_transcript_from_store(tmp_path: Path) -> None:
    store = MemoryStore(
        workspace_root=tmp_path,
        repository=None,
    )
    row = {"role": "user", "content": "x", "ts": "2026-01-01T00:00:00Z"}
    store.write_document("transcript.jsonl", json.dumps(row) + "\n")
    msgs = load_transcript_from_store(store, "transcript.jsonl")
    assert len(msgs) == 1
    assert msgs[0].content == "x"


def test_transcript_without_trailing_presence_signals_strips_trailing_presence_user() -> (
    None
):
    msgs = [
        ChatMessage(
            role="user",
            content="a",
            ts="2026-01-01T00:00:00Z",
            presence="repl_online",
        ),
        ChatMessage(role="assistant", content="b", ts="2026-01-01T00:01:00Z"),
        ChatMessage(
            role="user",
            content="presence only",
            ts="2026-01-01T00:02:00Z",
            presence="repl_online",
        ),
    ]
    out = transcript_without_trailing_presence_signals(msgs)
    assert len(out) == 2
    assert out[-1].role == "assistant"


def test_load_transcript_valid_jsonl(tmp_path: Path) -> None:
    from app.core.agentic_kernel.companion.memory_registry import get_memory_store

    root = tmp_path
    store = get_memory_store(root)
    rows = [
        {"role": "user", "content": "a", "ts": "2026-01-01T00:00:00Z"},
        {"role": "assistant", "content": "b", "timestamp": "2026-01-01T00:01:00Z"},
    ]
    store.write_document(
        "transcript.jsonl", "\n".join(json.dumps(r) for r in rows) + "\n"
    )
    msgs = load_transcript(root / "transcript.jsonl")
    assert len(msgs) == 2
    assert msgs[0].role == "user" and msgs[0].content == "a"
    assert msgs[1].role == "assistant" and msgs[1].content == "b"
