from __future__ import annotations

from pathlib import Path

from app.core.companion_harness.companion.ai_private_prompt import (
    AI_PRIVATE_SURFACED_KIND,
    append_ai_private_thought,
    get_ai_private_jsonl_text_for_prompt,
    load_ai_private_thoughts,
    mark_ai_private_surfaced,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    AI_PRIVATE_JSONL_REL,
)
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)
from app.core.companion_harness.companion.scope import CompanionScope


def test_ai_private_persistence_path_matches_scope_accessor() -> None:
    assert (
        DEFAULT_MEMORY_STORE_SCOPE_PATHS.ai_private_jsonl == AI_PRIVATE_JSONL_REL
    )


def test_get_ai_private_jsonl_extracts_text_field(tmp_path: Path) -> None:
    sc = CompanionScope("ap", "a", f"jl-{tmp_path.name}")
    store = MemoryStore(scope=sc, repository=None)
    store.write_document(
        AI_PRIVATE_JSONL_REL,
        '{"text": "first note"}\n{"content": "second"}\n',
    )
    out = get_ai_private_jsonl_text_for_prompt(store)
    assert out == "first note\nsecond"


def test_structured_thought_and_surfaced_marker(tmp_path: Path) -> None:
    sc = CompanionScope("ap", "a", f"st-{tmp_path.name}")
    store = MemoryStore(scope=sc, repository=None)
    thought = append_ai_private_thought(
        store, text="structured thought", after_user_msg_uuid=None
    )
    assert load_ai_private_thoughts(store) == [thought]
    mark_ai_private_surfaced(store, [thought.uuid])
    assert load_ai_private_thoughts(store) == []
    raw = store.read_document(AI_PRIVATE_JSONL_REL)
    assert AI_PRIVATE_SURFACED_KIND in raw
    assert get_ai_private_jsonl_text_for_prompt(store) == ""
