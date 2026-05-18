"""WebSocket connection lifecycle audit rows in ``.companion_runtime_events.jsonl``.

Records ``user_signed_on``, ``user_signed_out``, and ``ws_conn_dropped`` with client-local
``ts`` for behavior-pattern analysis. Greeting completion is inferred from transcript
``assistant.reply_to``, not from these rows.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from app.core.companion_harness.companion.runtime_events import append_runtime_event
from app.core.companion_harness.memory.memory_store import MemoryStore

_MISSING_UUID = "-"


class CompanionWsLifecycleEventKind(StrEnum):
    USER_SIGNED_ON = "user_signed_on"
    USER_SIGNED_OUT = "user_signed_out"
    WS_CONN_DROPPED = "ws_conn_dropped"


class CompanionWsLifecycleEvent(BaseModel):
    ts: str
    timezone: str
    kind: CompanionWsLifecycleEventKind
    user_id: str
    agent_id: str
    chat_id: str
    received_message_uuid: str
    ws_conn_id: str
    ws_close_code: int | str | None = None
    ws_close_reason: str | None = None


def _record_ws_lifecycle_event(
    store: MemoryStore,
    *,
    kind: CompanionWsLifecycleEventKind,
    ts: str,
    timezone_label: str,
    user_id: str,
    agent_id: str,
    chat_id: str,
    received_message_uuid: str,
    ws_conn_id: str,
    ws_close_code: int | str | None = None,
    ws_close_reason: str | None = None,
) -> None:
    event = CompanionWsLifecycleEvent(
        ts=ts,
        timezone=timezone_label,
        kind=kind,
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_id,
        received_message_uuid=received_message_uuid,
        ws_conn_id=ws_conn_id,
        ws_close_code=ws_close_code,
        ws_close_reason=ws_close_reason,
    )
    append_runtime_event(store, event.model_dump(mode="json", exclude_none=True))


def record_user_signed_on(
    store: MemoryStore,
    *,
    ts: str,
    timezone_label: str,
    user_id: str,
    agent_id: str,
    chat_id: str,
    received_message_uuid: str,
    ws_conn_id: str,
) -> None:
    _record_ws_lifecycle_event(
        store,
        kind=CompanionWsLifecycleEventKind.USER_SIGNED_ON,
        ts=ts,
        timezone_label=timezone_label,
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_id,
        received_message_uuid=received_message_uuid,
        ws_conn_id=ws_conn_id,
    )


def record_user_signed_out(
    store: MemoryStore,
    *,
    ts: str,
    timezone_label: str,
    user_id: str,
    agent_id: str,
    chat_id: str,
    received_message_uuid: str,
    ws_conn_id: str,
) -> None:
    _record_ws_lifecycle_event(
        store,
        kind=CompanionWsLifecycleEventKind.USER_SIGNED_OUT,
        ts=ts,
        timezone_label=timezone_label,
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_id,
        received_message_uuid=received_message_uuid,
        ws_conn_id=ws_conn_id,
    )


def record_ws_conn_dropped(
    store: MemoryStore,
    *,
    ts: str,
    timezone_label: str,
    user_id: str,
    agent_id: str,
    chat_id: str,
    received_message_uuid: str,
    ws_conn_id: str,
    ws_close_code: int | str,
    ws_close_reason: str,
) -> None:
    _record_ws_lifecycle_event(
        store,
        kind=CompanionWsLifecycleEventKind.WS_CONN_DROPPED,
        ts=ts,
        timezone_label=timezone_label,
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_id,
        received_message_uuid=received_message_uuid,
        ws_conn_id=ws_conn_id,
        ws_close_code=ws_close_code,
        ws_close_reason=ws_close_reason,
    )


def normalize_received_message_uuid_for_lifecycle(raw: str) -> str:
    """Map empty client message id to ``-`` for lifecycle JSONL."""
    stripped = raw.strip()
    if stripped:
        return stripped
    return _MISSING_UUID
