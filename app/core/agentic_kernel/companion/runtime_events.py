"""Append-only runtime exceptional events surfaced via companion_runtime_inspect.

Events are stored as JSON lines at workspace-relative path ``.companion_runtime_events.jsonl``
through :class:`~app.core.agentic_kernel.companion.memory_store.MemoryStore` only (never raw
``Path.write_text``). With a repository-backed store this persists like ``transcript.jsonl``;
without a repository the store keeps an in-memory snapshot per process."""

from __future__ import annotations

import json
from typing import Any

from .memory_store import MemoryStore

RUNTIME_EVENTS_REL_PATH = ".companion_runtime_events.jsonl"


def append_runtime_event(store: MemoryStore, record: dict[str, Any]) -> None:
    """Append one JSON object as a single line (JSONL) via MemoryStore."""
    store.append_jsonl_record(RUNTIME_EVENTS_REL_PATH, record)


def read_runtime_events(
    store: MemoryStore,
    *,
    kinds: set[str] | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return up to ``limit`` newest events (by ``ts`` descending)."""
    raw = store.read_document_if_exists(RUNTIME_EVENTS_REL_PATH)
    if not raw:
        return []
    rows: list[dict[str, Any]] = []
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    if kinds is not None:
        rows = [r for r in rows if str(r.get("kind") or "") in kinds]
    rows.sort(key=lambda r: str(r.get("ts") or ""), reverse=True)
    return rows[: max(0, limit)]


def has_unacknowledged_events_of_kind(
    store: MemoryStore,
    *,
    kind: str,
    since_ts: str | None,
) -> bool:
    """True if any event of ``kind`` has ``ts`` strictly after ``since_ts`` (or ``since_ts`` is None)."""
    cap = 512
    events = read_runtime_events(store, kinds={kind}, limit=cap)
    for ev in events:
        ts = str(ev.get("ts") or "")
        if since_ts is None or ts > since_ts:
            return True
    return False
