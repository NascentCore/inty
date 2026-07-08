from __future__ import annotations

import json
from pathlib import Path


from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    TRANSCRIPT_JSONL_REL,
)
from app.core.companion_harness.memory.memory_store_scope import (
    load_template_seed_text,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.models import (
    TRANSCRIPT_WINDOW_MAX_MESSAGES,
    AI_PRIVATE_SPLICE_MANIFEST_SOURCE,
    ChatMessage,
    ContextMeta,
    InnerTickKind,
    TranscriptProjection,
    is_transcript_row_user_visible,
    load_prompt_bundle,
    load_transcript_from_store,
    load_transcript_projection_from_store,
    load_transcript_text,
    transcript_for_llm_turn,
    transcript_rows_user_visible,
    transcript_without_trailing_presence_signals,
)


def test_chat_message_basic() -> None:
    m = ChatMessage(
        role="user", content="hello", ts="2026-01-01T00:00:00+00:00"
    )
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


def test_load_prompt_bundle_reads_channels_from_memory_store(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("models", "a", f"{tmp_path.name}-channels"),
        repository=None,
    )
    store.write_document("CHANNELS.md", "# Channels\ncustom channel contract\n")
    bundle = load_prompt_bundle(store, meta=ContextMeta())
    assert bundle.channels_md == "# Channels\ncustom channel contract\n"


def test_load_prompt_bundle_loads_harness_from_package_template(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("models", "a", f"{tmp_path.name}-harness"),
        repository=None,
    )
    bundle = load_prompt_bundle(store, meta=ContextMeta())
    assert "Innate limits of the companion harness" in bundle.harness_md
    assert "only communicate in text" in bundle.harness_md


def test_load_prompt_bundle_loads_about_from_package_template(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("models", "a", f"{tmp_path.name}-about"),
        repository=None,
    )
    bundle = load_prompt_bundle(store, meta=ContextMeta())
    expected = load_template_seed_text("ABOUT.md").strip()
    assert bundle.about_md == expected
    assert "Describe how a user should interact" in bundle.about_md


def test_load_prompt_bundle_reads_companionship_from_memory_store(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("models", "a", f"{tmp_path.name}-companionship"),
        repository=None,
    )
    store.write_document(
        "COMPANIONSHIP.md",
        "# 我们的关系\n\n用户原话：异地恋人\n",
    )
    bundle = load_prompt_bundle(store, meta=ContextMeta())
    assert "异地恋人" in bundle.companionship_md


def test_context_meta_defaults() -> None:
    c = ContextMeta()
    assert c.context_mode == "intimate"
    assert c.workspace_bootstrap_user_interactive_completed is True
    assert c.companion_ws_session_system_written is True


def test_context_meta_normalizes_experience_profile_id() -> None:
    c = ContextMeta(context_mode="  PUBLIC ")
    assert c.context_mode == "public"


def test_context_meta_bootstrap_string_is_plain_unknown_profile() -> None:
    c = ContextMeta(context_mode="bootstrap")
    assert c.context_mode == "bootstrap"


def test_transcript_for_llm_turn_short() -> None:
    loaded = [
        ChatMessage(
            role="user", content=str(i), ts=f"2026-01-01T00:{i:02d}:00Z"
        )
        for i in range(19)
    ]
    assert transcript_for_llm_turn(loaded) == loaded


def test_transcript_for_llm_turn_truncate() -> None:
    loaded = [
        ChatMessage(
            role="user", content=str(i), ts=f"2026-01-01T00:{i:02d}:00Z"
        )
        for i in range(25)
    ]
    out = transcript_for_llm_turn(loaded)
    assert len(out) == TRANSCRIPT_WINDOW_MAX_MESSAGES
    assert out[0].content == str(25 - TRANSCRIPT_WINDOW_MAX_MESSAGES)


def test_transcript_for_llm_turn_custom_window() -> None:
    loaded = [
        ChatMessage(
            role="user", content=str(i), ts=f"2026-01-01T00:{i:02d}:00Z"
        )
        for i in range(15)
    ]
    out = transcript_for_llm_turn(loaded, max_messages=8)
    assert len(out) == 8
    assert out[0].content == str(15 - 8)


def test_load_transcript_empty_store(tmp_path: Path) -> None:
    store = MemoryStore(
        scope=CompanionScope("models", "a", tmp_path.name),
        repository=None,
    )
    assert load_transcript_from_store(store, TRANSCRIPT_JSONL_REL) == []


def test_load_transcript_text() -> None:
    text = (
        '{"role": "user", "content": "a", "ts": "2026-01-01T00:00:00Z"}\n'
        '{"role": "assistant", "content": "b", "timestamp": "2026-01-01T00:01:00Z"}\n'
    )
    msgs = load_transcript_text(text)
    assert len(msgs) == 2


def test_load_transcript_from_store_roundtrip(tmp_path: Path) -> None:
    store = MemoryStore(
        scope=CompanionScope("models", "a", f"{tmp_path.name}-rt"),
        repository=None,
    )
    row = {"role": "user", "content": "x", "ts": "2026-01-01T00:00:00Z"}
    store.write_document(TRANSCRIPT_JSONL_REL, json.dumps(row) + "\n")
    msgs = load_transcript_from_store(store, TRANSCRIPT_JSONL_REL)
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
    store = MemoryStore(
        scope=CompanionScope("models", "a", f"{tmp_path.name}-vj"),
        repository=None,
    )
    rows = [
        {"role": "user", "content": "a", "ts": "2026-01-01T00:00:00Z"},
        {
            "role": "assistant",
            "content": "b",
            "timestamp": "2026-01-01T00:01:00Z",
        },
    ]
    store.write_document(
        TRANSCRIPT_JSONL_REL, "\n".join(json.dumps(r) for r in rows) + "\n"
    )
    msgs = load_transcript_from_store(store, TRANSCRIPT_JSONL_REL)
    assert len(msgs) == 2
    assert msgs[0].role == "user" and msgs[0].content == "a"
    assert msgs[1].role == "assistant" and msgs[1].content == "b"


def test_is_transcript_row_user_visible_filters_manifest_and_proactive_user() -> (
    None
):
    manifest = ChatMessage(
        role="system",
        content="[ai_private_splice]",
        ts="2026-01-01T00:00:00Z",
        source=AI_PRIVATE_SPLICE_MANIFEST_SOURCE,
    )
    proactive = ChatMessage(
        role="user",
        content="[SYSTEM PROACTIVE CHAT]",
        ts="2026-01-01T00:01:00Z",
        inner_tick_kind=InnerTickKind.PROACTIVE_CHAT,
    )
    real_user = ChatMessage(
        role="user", content="hi", ts="2026-01-01T00:02:00Z"
    )
    scheduled = ChatMessage(
        role="user",
        content="reminder",
        ts="2026-01-01T00:03:00Z",
        inner_tick_kind=InnerTickKind.SCHEDULED,
    )
    assert not is_transcript_row_user_visible(manifest)
    assert not is_transcript_row_user_visible(proactive)
    assert is_transcript_row_user_visible(real_user)
    assert is_transcript_row_user_visible(scheduled)


def test_load_user_visible_transcript_projection_from_store(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("models", "a", f"{tmp_path.name}-uv"),
        repository=None,
    )
    rows = [
        {"role": "user", "content": "hi", "ts": "2026-01-01T00:00:00Z"},
        {
            "role": "system",
            "content": "[ai_private_splice]",
            "ts": "2026-01-01T00:01:00Z",
            "source": AI_PRIVATE_SPLICE_MANIFEST_SOURCE,
        },
        {
            "role": "user",
            "content": "[SYSTEM PROACTIVE CHAT]",
            "ts": "2026-01-01T00:02:00Z",
            "inner_tick_kind": "proactive_chat",
        },
    ]
    store.write_document(
        TRANSCRIPT_JSONL_REL, "\n".join(json.dumps(r) for r in rows) + "\n"
    )
    visible = load_transcript_projection_from_store(
        store, TRANSCRIPT_JSONL_REL, TranscriptProjection.USER_VISIBLE
    )
    assert transcript_rows_user_visible(visible) == visible
    assert len(visible) == 1
    assert visible[0].content == "hi"


def test_load_transcript_projection_from_store(tmp_path: Path) -> None:
    store = MemoryStore(
        scope=CompanionScope("models", "a", f"{tmp_path.name}-proj"),
        repository=None,
    )
    rows = [
        {"role": "user", "content": "hi", "ts": "2026-01-01T00:00:00Z"},
        {
            "role": "system",
            "content": "[ai_private_splice]",
            "ts": "2026-01-01T00:01:00Z",
            "source": AI_PRIVATE_SPLICE_MANIFEST_SOURCE,
        },
    ]
    store.write_document(
        TRANSCRIPT_JSONL_REL, "\n".join(json.dumps(r) for r in rows) + "\n"
    )
    full = load_transcript_projection_from_store(
        store, TRANSCRIPT_JSONL_REL, TranscriptProjection.FULL
    )
    visible = load_transcript_projection_from_store(
        store, TRANSCRIPT_JSONL_REL, TranscriptProjection.USER_VISIBLE
    )
    assert len(full) == 2
    assert len(visible) == 1
