from __future__ import annotations

from app.core.companion_harness.companion.runtime_events import (
    USER_SIGNED_OUT_RUNTIME_EVENT_KIND,
    WS_CONN_DROPPED_RUNTIME_EVENT_KIND,
    append_runtime_event,
    build_user_signed_out_runtime_event_record,
    build_ws_conn_dropped_runtime_event_record,
    read_runtime_events,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore


def test_ws_channel_runtime_events_append_and_read(tmp_path) -> None:
    scope = CompanionScope("ws-ev", "agent-1", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)

    signed_out = build_user_signed_out_runtime_event_record(
        user_id="user-1",
        agent_id="agent-1",
        chat_id=99,
        received_message_uuid="aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee",
    )
    append_runtime_event(store, signed_out)

    dropped = build_ws_conn_dropped_runtime_event_record(
        user_id="user-1",
        agent_id="agent-1",
        chat_id=99,
        client_dropped_at_utc="2026-05-11T12:00:00+00:00",
        ws_close_code=1006,
        ws_close_reason="connection reset",
        received_message_uuid="-",
    )
    append_runtime_event(store, dropped)

    out_rows = read_runtime_events(
        store,
        kinds={USER_SIGNED_OUT_RUNTIME_EVENT_KIND},
        limit=5,
    )
    assert len(out_rows) == 1
    assert out_rows[0]["kind"] == USER_SIGNED_OUT_RUNTIME_EVENT_KIND
    assert (
        out_rows[0]["received_message_uuid"]
        == "aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee"
    )

    drop_rows = read_runtime_events(
        store,
        kinds={WS_CONN_DROPPED_RUNTIME_EVENT_KIND},
        limit=5,
    )
    assert len(drop_rows) == 1
    assert drop_rows[0]["ws_close_code"] == 1006
    assert drop_rows[0]["ws_close_reason"] == "connection reset"
