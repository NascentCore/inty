from __future__ import annotations

from pathlib import Path

from app.core.companion_harness.companion.ai_private_prompt import (
    AI_PRIVATE_SURFACED_KIND,
    append_ai_private_thought,
    get_ai_private_jsonl_text_for_prompt,
    get_ai_private_merged_text_for_prompt,
    get_ai_private_text_for_prompt,
    load_ai_private_thoughts,
    mark_ai_private_surfaced,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.companion.scope import CompanionScope


def test_get_ai_private_text_md_only(tmp_path: Path) -> None:
    sc = CompanionScope("ap", "a", f"md-{tmp_path.name}")
    store = MemoryStore(scope=sc, repository=None)
    store.write_document("ai_private.md", "hello md\n")
    assert get_ai_private_text_for_prompt(store) == "hello md\n"


def test_get_ai_private_jsonl_extracts_text_field(tmp_path: Path) -> None:
    sc = CompanionScope("ap", "a", f"jl-{tmp_path.name}")
    store = MemoryStore(scope=sc, repository=None)
    store.write_document(
        "ai_private.jsonl",
        '{"text": "first note"}\n{"content": "second"}\n',
    )
    out = get_ai_private_jsonl_text_for_prompt(store)
    assert out == "first note\nsecond"


def test_get_ai_private_merged_prefers_md_then_jsonl(tmp_path: Path) -> None:
    sc = CompanionScope("ap", "a", f"mg-{tmp_path.name}")
    store = MemoryStore(scope=sc, repository=None)
    store.write_document("ai_private.md", "from md")
    store.write_document("ai_private.jsonl", '{"note": "from jl"}\n')
    out = get_ai_private_merged_text_for_prompt(store)
    assert "from md" in out
    assert "from jl" in out
    assert "ai_private.jsonl" in out


def test_get_ai_private_merged_without_jsonl_equals_md(tmp_path: Path) -> None:
    sc = CompanionScope("ap", "a", f"eq-{tmp_path.name}")
    store = MemoryStore(scope=sc, repository=None)
    store.write_document("ai_private.md", "only md\n")
    assert get_ai_private_merged_text_for_prompt(
        store
    ) == get_ai_private_text_for_prompt(store)


def test_structured_thought_and_surfaced_marker(tmp_path: Path) -> None:
    sc = CompanionScope("ap", "a", f"st-{tmp_path.name}")
    store = MemoryStore(scope=sc, repository=None)
    thought = append_ai_private_thought(
        store, text="structured thought", after_user_msg_uuid=None
    )
    assert load_ai_private_thoughts(store) == [thought]
    mark_ai_private_surfaced(store, [thought.uuid])
    assert load_ai_private_thoughts(store) == []
    raw = store.read_document("ai_private.jsonl")
    assert AI_PRIVATE_SURFACED_KIND in raw
    assert get_ai_private_jsonl_text_for_prompt(store) == ""
