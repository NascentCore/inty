from __future__ import annotations

from pathlib import Path
from threading import Event

from app.core.companion_harness.companion.models import ChatMessage
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.dreaming_consolidation import (
    consolidate_memory_during_dreaming,
)
from app.core.companion_harness.memory.memory_store import MemoryStore


def test_consolidate_memory_during_dreaming_curates_applicable_docs(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("dream-mem", "agent", tmp_path.name),
        repository=None,
    )
    for rel in ("MEMORY.md", "USER.md", "STYLE.md", "SOUL.md", "COMPANIONSHIP.md"):
        store.write_document(rel, f"{rel} seed\n")
    rows = [
        ChatMessage(
            role="user",
            content="I like quiet mornings",
            ts="2026-01-02T09:00:00+00:00",
            uuid="u",
        ),
        ChatMessage(
            role="assistant",
            content="I'll remember that gently.",
            ts="2026-01-02T09:01:00+00:00",
            uuid="a",
        ),
    ]
    roles: list[str] = []

    def complete_fn(messages: list[dict[str, object]], role: str) -> str:
        roles.append(role)
        return f"{role} curated"

    tool_bg_idle = Event()
    tool_bg_idle.set()
    assert (
        consolidate_memory_during_dreaming(
            store,
            rows,
            complete_fn,
            tool_bg_idle_event=tool_bg_idle,
        )
        is True
    )
    assert roles == [
        "dreaming_day_summary",
        "memory",
        "user",
        "style",
        "soul",
        "companionship",
    ]
    daily = store.read_document("memory/daily/2026-01-02.md")
    assert daily == "dreaming_day_summary curated\n"
    assert store.read_document_if_exists("memory/2026-01-02.md") is None
    assert store.read_document("MEMORY.md") == "memory curated\n"
    assert store.read_document("USER.md") == "user curated\n"
    assert store.read_document("STYLE.md") == "style curated\n"
    assert store.read_document("SOUL.md") == "soul curated\n"
    assert store.read_document("COMPANIONSHIP.md") == "companionship curated\n"
