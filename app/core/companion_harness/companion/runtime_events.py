"""Append-only runtime exceptional events persisted in MemoryStore.

Known ``kind`` values include ``llm_inference_failure`` (every failed companion
``chat.completions`` via ``llm.chat_completions.create_chat_completion_sync`` plus structured-chat
foreground timeouts when correlation ContextVar is bound), ``tool_background_failure`` (async tool
loop thread in ``tool_background`` when the error is not already logged as an LLM inference failure),
``user_signed_out`` and ``ws_conn_dropped`` (WebSocket control-frame audit from ``chat_ws.py``),
``inner_tick_dreaming`` (sleeping-state memory batch from inner-tick poll slot 4;
see ``dreaming_observability``), and ad-hoc operator/test entries such as ``tool_timeout``.

Events are stored as JSON lines at workspace-relative path ``.companion_runtime_events.jsonl``
through :class:`~app.core.companion_harness.memory.memory_store.MemoryStore` only (never raw
``Path.write_text``). With a repository-backed store this persists like ``transcript.jsonl``;
without a repository the store keeps an in-memory snapshot per process.

TODO(#3773): Relationship-signal events (CRS bond signals) should use a
dedicated append-only JSONL, not exceptional runtime kinds here — #3773 (epic #3341).

Each successful append emits a short **loguru** line: ``INFO`` for ``llm_inference_failure`` and
``tool_background_failure`` kinds, ``DEBUG`` for other kinds (see ``append_runtime_event``).
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)

from .utc import utc_iso_ts

USER_SIGNED_OUT_RUNTIME_EVENT_KIND = "user_signed_out"
WS_CONN_DROPPED_RUNTIME_EVENT_KIND = "ws_conn_dropped"


def build_user_signed_out_runtime_event_record(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    received_message_uuid: str,
) -> dict[str, Any]:
    """JSONL record for ``user_signed_out`` (fields match former ``CHAT_LOGS.md`` line)."""
    return {
        "ts": utc_iso_ts(),
        "kind": USER_SIGNED_OUT_RUNTIME_EVENT_KIND,
        "user_id": user_id,
        "agent_id": agent_id,
        "chat_id": str(chat_id),
        "received_message_uuid": received_message_uuid,
    }


def build_ws_conn_dropped_runtime_event_record(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    client_dropped_at_utc: str,
    ws_close_code: str | int,
    ws_close_reason: str,
    received_message_uuid: str,
) -> dict[str, Any]:
    """JSONL record for ``ws_conn_dropped`` (fields match former ``CHAT_LOGS.md`` line)."""
    return {
        "ts": utc_iso_ts(),
        "kind": WS_CONN_DROPPED_RUNTIME_EVENT_KIND,
        "user_id": user_id,
        "agent_id": agent_id,
        "chat_id": str(chat_id),
        "client_dropped_at_utc": client_dropped_at_utc,
        "ws_close_code": ws_close_code,
        "ws_close_reason": ws_close_reason,
        "received_message_uuid": received_message_uuid,
    }


def append_runtime_event(store: MemoryStore, record: dict[str, Any]) -> None:
    """Append one JSON object as a single line (JSONL) via MemoryStore."""
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.companion_runtime_events_jsonl
    store.append_jsonl_record(rel, record)
    kind = str(record.get("kind") or "")
    tid = str(record.get("trace_id") or "").strip()
    uid = str(record.get("user_msg_uuid") or "").strip()
    tail = f" trace_id={tid}" if tid else ""
    tail += f" user_msg_uuid={uid}" if uid else ""
    msg = f"companion_runtime_event kind={kind!r}{tail}"
    if kind in ("llm_inference_failure", "tool_background_failure"):
        logger.info(msg)
    else:
        logger.debug(msg)


def read_runtime_events(
    store: MemoryStore,
    *,
    kinds: set[str] | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return up to ``limit`` newest events (by ``ts`` descending)."""
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.companion_runtime_events_jsonl
    raw = store.read_document_if_exists(rel)
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
