"""WebSocket connection lifecycle audit rows in ``.companion_runtime_events.jsonl``.

Records ``user_signed_on``, ``user_signed_out``, and ``ws_conn_dropped`` with client-local
``ts`` for behavior-pattern analysis. Greeting completion is inferred from transcript
``assistant.reply_to``, not from these rows.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any
from zoneinfo import ZoneInfo

from loguru import logger
from pydantic import BaseModel

from app.core.companion_harness.companion.runtime_events import append_runtime_event
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.schemas.chat import UserTimeContext

_MISSING_TIMEZONE = "-"
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


def _timezone_label_from_context(utc: UserTimeContext) -> str:
    tz = (utc.timezone or "").strip()
    if tz:
        return tz
    return _MISSING_TIMEZONE


def _zone_from_user_time_context(utc: UserTimeContext) -> timezone | ZoneInfo | None:
    tz_name = (utc.timezone or "").strip()
    if tz_name:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            pass
    offset = utc.utc_offset_minutes
    if offset is not None:
        return timezone(timedelta(minutes=int(offset)))
    return None


def _parse_utc_instant(raw: str) -> datetime | None:
    text = raw.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _format_local_wall_clock(instant_utc: datetime, tz: timezone | ZoneInfo) -> str:
    local = instant_utc.astimezone(tz)
    return local.isoformat(timespec="seconds")


def resolve_client_local_ts_for_ws_lifecycle(
    *,
    tc_box: list[Any | None],
    dropped_at_utc: str | None,
) -> tuple[str, str] | None:
    """Return ``(ts, timezone)`` for lifecycle runtime rows, or ``None`` to skip append."""
    utc: UserTimeContext | None = None
    if tc_box:
        raw = tc_box[0]
        if raw:
            try:
                utc = UserTimeContext.model_validate(raw)
            except Exception:
                utc = None
    if utc is not None:
        local_time = (utc.local_time or "").strip()
        if local_time:
            return local_time, _timezone_label_from_context(utc)
        drop_raw = (dropped_at_utc or "").strip()
        if drop_raw:
            instant = _parse_utc_instant(drop_raw)
            tz = _zone_from_user_time_context(utc)
            if instant is not None and tz is not None:
                return _format_local_wall_clock(instant, tz), _timezone_label_from_context(utc)
    return None


def _append_ws_lifecycle_event(store: MemoryStore, event: CompanionWsLifecycleEvent) -> None:
    try:
        append_runtime_event(store, event.model_dump(mode="json", exclude_none=True))
    except Exception:
        logger.warning(
            "append_ws_lifecycle_event failed kind={} user_id={} agent_id={} chat_id={}",
            event.kind.value,
            event.user_id,
            event.agent_id,
            event.chat_id,
            exc_info=True,
        )


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
    event = CompanionWsLifecycleEvent(
        ts=ts,
        timezone=timezone_label,
        kind=CompanionWsLifecycleEventKind.USER_SIGNED_ON,
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_id,
        received_message_uuid=received_message_uuid,
        ws_conn_id=ws_conn_id,
    )
    _append_ws_lifecycle_event(store, event)


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
    event = CompanionWsLifecycleEvent(
        ts=ts,
        timezone=timezone_label,
        kind=CompanionWsLifecycleEventKind.USER_SIGNED_OUT,
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_id,
        received_message_uuid=received_message_uuid,
        ws_conn_id=ws_conn_id,
    )
    _append_ws_lifecycle_event(store, event)


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
    event = CompanionWsLifecycleEvent(
        ts=ts,
        timezone=timezone_label,
        kind=CompanionWsLifecycleEventKind.WS_CONN_DROPPED,
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_id,
        received_message_uuid=received_message_uuid,
        ws_conn_id=ws_conn_id,
        ws_close_code=ws_close_code,
        ws_close_reason=ws_close_reason,
    )
    _append_ws_lifecycle_event(store, event)


def normalize_received_message_uuid_for_lifecycle(raw: str) -> str:
    """Map empty client message id to ``-`` for lifecycle JSONL."""
    stripped = raw.strip()
    if stripped:
        return stripped
    return _MISSING_UUID
