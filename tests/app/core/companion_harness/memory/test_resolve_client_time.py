"""Tests for temporary launch ``resolve_client_time`` precedence."""

from __future__ import annotations

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.client_time_from_memory_store import (
    resolve_client_time,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.schemas.chat import UserTimeContext


def _store(tmp_path) -> MemoryStore:
    return MemoryStore(
        scope=CompanionScope("u", "a", str(tmp_path.resolve())),
        repository=None,
    )


def test_resolve_client_time_prefers_incoming_timezone(tmp_path) -> None:
    store = _store(tmp_path)
    store.write_document(
        "USER.md",
        "## 身份信息\n\n- 时区：Asia/Tokyo\n",
    )
    incoming = UserTimeContext(
        local_time="2026-05-01T10:00:00",
        timezone="America/New_York",
        utc_offset_minutes=-240,
    )

    ctx = resolve_client_time(
        store=store,
        incoming=incoming,
        default_user_time_zone="America/Los_Angeles",
    )

    assert ctx is not None
    assert ctx.timezone == "America/New_York"


def test_resolve_client_time_user_md_beats_config_default(tmp_path) -> None:
    store = _store(tmp_path)
    store.write_document(
        "USER.md",
        "## 身份信息\n\n- 时区：Asia/Tokyo\n",
    )

    ctx = resolve_client_time(
        store=store,
        incoming=None,
        default_user_time_zone="America/Los_Angeles",
    )

    assert ctx is not None
    assert ctx.timezone == "Asia/Tokyo"


def test_resolve_client_time_config_default_when_no_user_md_tz(
    tmp_path,
) -> None:
    store = _store(tmp_path)
    store.write_document("USER.md", "## 身份信息\n\n- 姓名：Alex\n")

    ctx = resolve_client_time(
        store=store,
        incoming=None,
        default_user_time_zone="America/Los_Angeles",
    )

    assert ctx is not None
    assert ctx.timezone == "America/Los_Angeles"


def test_resolve_client_time_unresolved_when_config_disabled(tmp_path) -> None:
    store = _store(tmp_path)

    ctx = resolve_client_time(
        store=store,
        incoming=None,
        default_user_time_zone=None,
    )

    assert ctx is None
