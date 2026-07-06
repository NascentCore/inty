"""Merge ``living_sphere_updates.jsonl`` into ``LIVING_SPHERE.md`` during dreaming consolidation."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from typing import Any

from loguru import logger

from app.core.companion_harness.memory.memory_store_path_constants import (
    LIVING_SPHERE_MD_REL,
    LIVING_SPHERE_UPDATES_JSONL_REL,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)
from app.core.config import global_config_loaded_from_config_yaml
from app.living_sphere.models import (
    LivingSphereUpdate,
)
from app.living_sphere.seeding import (
    ensure_living_sphere_seeded,
)

_PIPELINE_CURSOR_KEY = "living_sphere_curated_through_update_id"
_PENDING_UPDATES_BATCH_CAP = 20
_MAX_COMPACT_BATCHES_PER_TURN = 50
_USER_EXPRESSION_MARKER = "对用户表达"
_LIVING_SPHERE_TITLE_MARKERS = ("# LIVING SPHERE", "# LIVING_SPHERE")
_MIN_SUBSTANTIVE_CHARS = 80

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


class LivingSphereCuratorOutputRejected(ValueError):
    """Curator LLM output failed structural validation; cursor must not advance."""


def living_sphere_curator_output_rejection_reason(body: str) -> str | None:
    """Return a short reason when ``body`` must not replace LIVING_SPHERE.md, else None."""
    text = body.strip()
    if len(text) < _MIN_SUBSTANTIVE_CHARS:
        return (
            f"substantive content shorter than {_MIN_SUBSTANTIVE_CHARS} chars"
        )
    if _USER_EXPRESSION_MARKER not in text:
        return f"missing {_USER_EXPRESSION_MARKER!r} line"
    if not any(marker in text for marker in _LIVING_SPHERE_TITLE_MARKERS):
        return "missing LIVING SPHERE title heading"
    return None


def _tool_bg_idle_wait_timeout_sec() -> float:
    return float(
        global_config_loaded_from_config_yaml.agent.companion_harness.tool_bg_idle_wait_timeout_sec
    )


def wait_for_tool_background_before_living_sphere_compact(
    tool_bg_idle_event: threading.Event,
    *,
    scope_registry_key: str,
) -> None:
    """Let async tool_background finish appending jsonl before LivingSphere compact."""
    if tool_bg_idle_event.is_set():
        return
    timeout_s = _tool_bg_idle_wait_timeout_sec()
    logger.debug(
        "living_sphere_curator waiting for tool_background idle scope={} timeout_s={:.0f}",
        scope_registry_key,
        timeout_s,
    )
    if not tool_bg_idle_event.wait(timeout=timeout_s):
        logger.warning(
            "living_sphere_curator tool_background idle wait timed out scope={} timeout_s={:.0f}",
            scope_registry_key,
            timeout_s,
        )


def _load_curator_state(store: MemoryStore) -> dict[str, object]:
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.living_sphere_curator_state_json
    raw = store.read_document_if_exists(rel)
    if raw is None or not raw.strip():
        return {}
    loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        raise ValueError(f"{rel} must be a JSON object")
    return loaded


def _write_curator_state(store: MemoryStore, data: dict[str, object]) -> None:
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.living_sphere_curator_state_json
    store.write_document(
        rel, json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    )


def _curator_curated_through_update_id(state: dict[str, object]) -> str:
    """Last ``LivingSphereUpdate.update_id`` merged into LIVING_SPHERE.md; ``""`` if never compacted."""
    cursor_raw = state.get(_PIPELINE_CURSOR_KEY)
    if isinstance(cursor_raw, str):
        return cursor_raw.strip()
    return ""


def _read_all_updates(store: MemoryStore) -> list[LivingSphereUpdate]:
    raw = store.read_document_if_exists(LIVING_SPHERE_UPDATES_JSONL_REL)
    if raw is None or not raw.strip():
        return []
    out: list[LivingSphereUpdate] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(LivingSphereUpdate.model_validate(json.loads(line)))
    return out


def _pending_updates_after_cursor(
    rows: list[LivingSphereUpdate],
    *,
    curated_through_update_id: str,
) -> tuple[list[LivingSphereUpdate], bool]:
    """Rows not yet merged into LIVING_SPHERE.md, in jsonl file order.

    ``curated_through_update_id`` is the last ``update_id`` written by a successful compact
    (stored in ``.companion_living_sphere_curator.json`` as ``living_sphere_curated_through_update_id``).
    Use ``""`` when no compact has run yet—all rows are pending.

    Returns ``(pending_rows, cursor_missing)``. ``cursor_missing`` is True when
    ``curated_through_update_id`` is non-empty but does not appear in ``rows`` (stale cursor);
    callers re-merge all rows in that case.
    """
    if not rows:
        return [], False
    if not curated_through_update_id:
        return rows, False
    pending: list[LivingSphereUpdate] = []
    found = False
    for row in rows:
        if not found:
            if row.update_id == curated_through_update_id:
                found = True
            continue
        pending.append(row)
    if not found:
        return rows, True
    return pending, False


def compact_living_sphere_batch(
    store: MemoryStore,
    batch: list[LivingSphereUpdate],
    complete_fn: Callable[[list[dict[str, Any]], str], str],
) -> str:
    """Run curator LLM for one batch; write LIVING_SPHERE.md; return last merged update_id."""
    ensure_living_sphere_seeded(store)
    current_md = store.read_document(LIVING_SPHERE_MD_REL)
    requests_block = "\n".join(
        f"- [{u.update_id}] {u.change_request}" for u in batch
    )
    user_block = (
        f"Current LIVING_SPHERE.md:\n\n{current_md}\n\n---\n\n"
        f"Pending change requests ({len(batch)}):\n{requests_block}\n"
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _LIVING_SPHERE_CURATOR_SYSTEM},
        {"role": "user", "content": user_block},
    ]
    new_body = complete_fn(messages, "memory").strip()
    reject = living_sphere_curator_output_rejection_reason(new_body)
    if reject is not None:
        raise LivingSphereCuratorOutputRejected(reject)
    store.write_document(LIVING_SPHERE_MD_REL, new_body + "\n")
    return batch[-1].update_id


def compact_living_sphere_if_pending(
    store: MemoryStore,
    complete_fn: Callable[[list[dict[str, Any]], str], str],
    *,
    tool_bg_idle_event: threading.Event,
) -> bool:
    """Drain pending jsonl in chronological batches. Returns True if any batch compacted."""
    wait_for_tool_background_before_living_sphere_compact(
        tool_bg_idle_event,
        scope_registry_key=store.scope.registry_key(),
    )
    any_ran = False
    scope = store.scope.registry_key()
    for _ in range(_MAX_COMPACT_BATCHES_PER_TURN):
        rows = _read_all_updates(store)
        state = _load_curator_state(store)
        cursor = _curator_curated_through_update_id(state)
        pending, cursor_missing = _pending_updates_after_cursor(
            rows, curated_through_update_id=cursor
        )
        if cursor_missing and cursor:
            logger.warning(
                "living_sphere_curator cursor not found in jsonl; re-merging all rows scope={} cursor={}",
                scope,
                cursor,
            )
        if not pending:
            break
        batch = pending[:_PENDING_UPDATES_BATCH_CAP]
        last_id = compact_living_sphere_batch(store, batch, complete_fn)
        state[_PIPELINE_CURSOR_KEY] = last_id
        _write_curator_state(store, state)
        any_ran = True
        if len(pending) <= _PENDING_UPDATES_BATCH_CAP:
            break
    else:
        rows_after = _read_all_updates(store)
        state_after = _load_curator_state(store)
        cursor_after = _curator_curated_through_update_id(state_after)
        still_pending, _ = _pending_updates_after_cursor(
            rows_after, curated_through_update_id=cursor_after
        )
        if still_pending:
            logger.error(
                "living_sphere_curator hit max batches per turn scope={} remaining_pending={}",
                scope,
                len(still_pending),
            )
    return any_ran
