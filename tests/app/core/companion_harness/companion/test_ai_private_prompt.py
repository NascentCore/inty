from __future__ import annotations

from pathlib import Path

from app.core.companion_harness.companion.ai_private_prompt import (
    get_ai_private_jsonl_text_for_prompt,
    get_ai_private_merged_text_for_prompt,
    get_ai_private_text_for_prompt,
)
from app.core.companion_harness.memory.memory_registry import (
    get_memory_store,
    shutdown_memory_store,
)
from app.core.companion_harness.companion.scope import CompanionScope


def test_get_ai_private_text_md_only(tmp_path: Path) -> None:
    sc = CompanionScope("ap", "a", f"md-{tmp_path.name}")
    store = get_memory_store(sc, dsn="")
    store.write_document("ai_private.md", "hello md\n")
    assert get_ai_private_text_for_prompt(store) == "hello md\n"
    shutdown_memory_store(sc)


def test_get_ai_private_jsonl_extracts_text_field(tmp_path: Path) -> None:
    sc = CompanionScope("ap", "a", f"jl-{tmp_path.name}")
    store = get_memory_store(sc, dsn="")
    store.write_document(
        "ai_private.jsonl",
        '{"text": "first note"}\n{"content": "second"}\n',
    )
    out = get_ai_private_jsonl_text_for_prompt(store)
    assert out == "first note\nsecond"
    shutdown_memory_store(sc)


def test_get_ai_private_merged_prefers_md_then_jsonl(tmp_path: Path) -> None:
    sc = CompanionScope("ap", "a", f"mg-{tmp_path.name}")
    store = get_memory_store(sc, dsn="")
    store.write_document("ai_private.md", "from md")
    store.write_document("ai_private.jsonl", '{"note": "from jl"}\n')
    out = get_ai_private_merged_text_for_prompt(store)
    assert "from md" in out
    assert "from jl" in out
    assert "ai_private.jsonl" in out
    shutdown_memory_store(sc)


def test_get_ai_private_merged_without_jsonl_equals_md(tmp_path: Path) -> None:
    sc = CompanionScope("ap", "a", f"eq-{tmp_path.name}")
    store = get_memory_store(sc, dsn="")
    store.write_document("ai_private.md", "only md\n")
    assert get_ai_private_merged_text_for_prompt(store) == get_ai_private_text_for_prompt(
        store
    )
    shutdown_memory_store(sc)
