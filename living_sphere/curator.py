"""Merge ``living_sphere_updates.jsonl`` into ``LIVING_SPHERE.md`` via memory-model LLM."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)
from living_sphere.models import (
    LIVING_SPHERE_UPDATES_JSONL_RELATIVE_PATH,
    LivingSphereUpdate,
)
from living_sphere.seeding import LIVING_SPHERE_RELATIVE_PATH

# TODO(offline-batch): Large-scale LivingSphere compact (cross-scope backfill / backlog) must be a
# separate deployable + managed cloud offline executor (cf. backend/push_worker)—NOT a longer cron
# on memory_pipeline. Reuse compact_* merge semantics only; batching, sharding, and cursor locking
# are offline concerns. Do not treat offline as a simple extension of per-turn online compact.

_PIPELINE_CURSOR_KEY = "living_sphere_curated_through_update_id"
_PENDING_UPDATES_CAP = 20
_LIVING_SPHERE_CURATOR_SYSTEM = """You are a LivingSphere curator. LIVING_SPHERE.md is the readable snapshot of the companion's private virtual home (shared with the user inside TechnoCore). It is injected into the system prompt on every turn.

Given the current LIVING_SPHERE.md and pending user-directed change requests (from living_sphere_updates.jsonl), output ONLY the full updated LIVING_SPHERE.md body (markdown).

Rules:
- Preserve the document's structure and tone when possible (title, 世界/名称/位置/锚点/当前默认位置/氛围, and the line starting with 「对用户表达」).
- Merge layout, objects, anchors, atmosphere, and default position changes from the change requests; deduplicate and resolve contradictions in favor of the clearest, most recent user intent.
- Do NOT alter TechnoCore collective-world facts beyond this companion's private home; do NOT claim real-world geographic coordinates.
- Keep 「对用户表达」 guidance intact (virtual-world location only; no pretending to be in the user's physical space).
- Output raw markdown only: no preamble, no code fences around the whole document.
- Write in the same language as the current LIVING_SPHERE.md (usually Chinese).
"""


def _load_pipeline_state(store: MemoryStore) -> dict[str, object]:
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.memory_pipeline_state_json
    raw = store.read_document_if_exists(rel)
    if raw is None or not raw.strip():
        return {}
    loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        raise ValueError(f"{rel} must be a JSON object")
    return loaded


def _write_pipeline_state(store: MemoryStore, data: dict[str, object]) -> None:
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.memory_pipeline_state_json
    store.write_document(rel, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def _read_all_updates(store: MemoryStore) -> list[LivingSphereUpdate]:
    raw = store.read_document_if_exists(LIVING_SPHERE_UPDATES_JSONL_RELATIVE_PATH)
    if raw is None or not raw.strip():
        return []
    out: list[LivingSphereUpdate] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(LivingSphereUpdate.model_validate(json.loads(line)))
    return out


def _pending_updates(
    rows: list[LivingSphereUpdate], *, curated_through_update_id: str | None
) -> list[LivingSphereUpdate]:
    if not rows:
        return []
    if not curated_through_update_id:
        pending = rows
    else:
        pending = []
        found = False
        for row in rows:
            if not found:
                if row.update_id == curated_through_update_id:
                    found = True
                continue
            pending.append(row)
        if not found:
            pending = rows
    if len(pending) > _PENDING_UPDATES_CAP:
        pending = pending[-_PENDING_UPDATES_CAP :]
    return pending


def compact_living_sphere(
    store: MemoryStore,
    pending: list[LivingSphereUpdate],
    complete_fn: Callable[[list[dict[str, Any]], str], str],
) -> str:
    """Run curator LLM; write LIVING_SPHERE.md; return last merged update_id."""
    current_md = store.read_document(LIVING_SPHERE_RELATIVE_PATH)
    requests_block = "\n".join(
        f"- [{u.update_id}] {u.change_request}" for u in pending
    )
    user_block = (
        f"Current LIVING_SPHERE.md:\n\n{current_md}\n\n---\n\n"
        f"Pending change requests ({len(pending)}):\n{requests_block}\n"
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _LIVING_SPHERE_CURATOR_SYSTEM},
        {"role": "user", "content": user_block},
    ]
    new_body = complete_fn(messages, "memory").strip()
    store.write_document(LIVING_SPHERE_RELATIVE_PATH, new_body + "\n")
    return pending[-1].update_id


def compact_living_sphere_if_pending(
    store: MemoryStore,
    complete_fn: Callable[[list[dict[str, Any]], str], str],
) -> bool:
    """Compact when jsonl rows exist after pipeline cursor. Returns True if curator ran."""
    rows = _read_all_updates(store)
    state = _load_pipeline_state(store)
    cursor_raw = state.get(_PIPELINE_CURSOR_KEY)
    cursor = cursor_raw.strip() if isinstance(cursor_raw, str) and cursor_raw.strip() else None
    pending = _pending_updates(rows, curated_through_update_id=cursor)
    if not pending:
        return False
    last_id = compact_living_sphere(store, pending, complete_fn)
    state[_PIPELINE_CURSOR_KEY] = last_id
    _write_pipeline_state(store, state)
    return True
