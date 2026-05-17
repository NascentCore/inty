"""Tests for WebSocket lifecycle rows in ``.companion_runtime_events.jsonl``."""

from __future__ import annotations

from app.core.companion_harness.companion.runtime_events import read_runtime_events
from app.core.companion_harness.companion.ws_lifecycle_events import (
    CompanionWsLifecycleEventKind,
    normalize_received_message_uuid_for_lifecycle,
    record_user_signed_on,
    resolve_client_local_ts_for_ws_lifecycle,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.companion.scope import CompanionScope


def test_resolve_client_local_ts_prefers_local_time() -> None:
    tc_box = [
        {
            "local_time": "2026-05-17T10:30:00+08:00",
            "timezone": "Asia/Shanghai",
            "utc_offset_minutes": 480,
        }
    ]
    resolved = resolve_client_local_ts_for_ws_lifecycle(
        tc_box=tc_box,
        dropped_at_utc=None,
    )
    assert resolved == ("2026-05-17T10:30:00+08:00", "Asia/Shanghai")


def test_resolve_client_local_ts_drop_converts_dropped_at_utc() -> None:
    tc_box = [
        {
            "timezone": "Asia/Shanghai",
            "utc_offset_minutes": 480,
        }
    ]
    resolved = resolve_client_local_ts_for_ws_lifecycle(
        tc_box=tc_box,
        dropped_at_utc="2026-05-17T02:30:00Z",
    )
    assert resolved is not None
    ts, tz = resolved
    assert tz == "Asia/Shanghai"
    assert "10:30:00" in ts


def test_resolve_client_local_ts_missing_returns_none() -> None:
    assert (
        resolve_client_local_ts_for_ws_lifecycle(tc_box=[None], dropped_at_utc=None)
        is None
    )


def test_record_user_signed_on_appends_jsonl(tmp_path) -> None:
    scope = CompanionScope("u1", "a1", f"chat-{tmp_path.name}")
    store = MemoryStore(scope=scope, repository=None)
    record_user_signed_on(
        store,
        ts="2026-05-17T09:00:00+08:00",
        timezone_label="Asia/Shanghai",
        user_id="u1",
        agent_id="a1",
        chat_id=7,
        received_message_uuid="11111111-2222-4333-8444-555555555555",
        ws_conn_id="22222222-3333-4333-8444-555555555555",
    )
    rows = read_runtime_events(
        store,
        kinds={CompanionWsLifecycleEventKind.USER_SIGNED_ON.value},
        limit=5,
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["kind"] == "user_signed_on"
    assert row["ts"] == "2026-05-17T09:00:00+08:00"
    assert row["timezone"] == "Asia/Shanghai"
    assert row["chat_id"] == 7
    assert row["received_message_uuid"] == "11111111-2222-4333-8444-555555555555"


def test_normalize_received_message_uuid_for_lifecycle() -> None:
    assert normalize_received_message_uuid_for_lifecycle("") == "-"
    assert (
        normalize_received_message_uuid_for_lifecycle("aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee")
        == "aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee"
    )
