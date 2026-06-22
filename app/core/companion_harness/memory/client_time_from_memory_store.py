"""Wall-clock context for agent-channel turns when the client cannot report device TZ.

TODO(#3391): Log timezone_source (client | user_md | transcript | none); replace
USER.md regex read with structured persistence.
TODO(#3411): Manual E2E smoke — Telegram/Weixin turn with persisted USER.md 时区 → LangSmith time slice.
TODO(issues/3586): Temporary launch default_user_time_zone config fallback; remove when
per-user TZ is reliable.
"""

from __future__ import annotations

from datetime import datetime

from loguru import logger
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.user_timezone_from_user_md import (
    infer_iana_timezone_from_user_md,
)
from app.schemas.chat import UserTimeContext

# TODO(memdoc-path-constants): Replace ad-hoc _USER_MD_REL with canonical constant. #3413
_USER_MD_REL = "USER.md"


def build_user_time_context_for_iana(tz_name: str) -> UserTimeContext:
    """Build ``UserTimeContext`` for one IANA timezone at the current instant."""
    assert tz_name.strip() != ""
    zone = ZoneInfo(tz_name.strip())
    now = datetime.now(tz=zone)
    offset = now.utcoffset()
    utc_mins = int(offset.total_seconds() // 60) if offset is not None else None
    return UserTimeContext(
        local_time=now.isoformat(timespec="milliseconds"),
        timezone=zone.key,
        utc_offset_minutes=utc_mins,
    )


def _valid_incoming_client_timezone(
    incoming: UserTimeContext | None,
) -> str | None:
    if incoming is None:
        return None
    tz = incoming.timezone
    if tz is None or tz.strip() == "":
        return None
    try:
        return ZoneInfo(tz.strip()).key
    except ZoneInfoNotFoundError:
        return None


def client_time_from_memory_store(store: MemoryStore) -> UserTimeContext | None:
    """Resolve client wall-clock facts from USER.md when timezone was inferred there."""
    user_md = store.read_document_if_exists(_USER_MD_REL)
    if user_md is None or not user_md.strip():
        return None
    tz_name = infer_iana_timezone_from_user_md(user_md)
    if tz_name is None:
        return None
    try:
        ctx = build_user_time_context_for_iana(tz_name)
    except ZoneInfoNotFoundError:
        logger.warning(
            "channel_user_time_context invalid user_md timezone={!r}",
            tz_name,
        )
        return None
    logger.debug(
        "channel_user_time_context source=user_md tz={}",
        ctx.timezone,
    )
    return ctx


def resolve_client_time(
    *,
    store: MemoryStore,
    incoming: UserTimeContext | None,
    default_user_time_zone: str | None,
) -> UserTimeContext | None:
    """Resolve wall-clock context: client TZ, then USER.md, then temporary config default."""
    client_tz = _valid_incoming_client_timezone(incoming)
    if client_tz is not None:
        return build_user_time_context_for_iana(client_tz)
    user_md_ctx = client_time_from_memory_store(store)
    if user_md_ctx is not None:
        return user_md_ctx
    if default_user_time_zone is not None:
        return build_user_time_context_for_iana(default_user_time_zone)
    return None
