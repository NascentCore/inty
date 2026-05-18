"""Tests for WebSocket lifecycle rows in ``.companion_runtime_events.jsonl``."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.companion_harness.companion.runtime_events import read_runtime_events
from app.core.companion_harness.companion.ws_lifecycle_events import (
    CompanionWsLifecycleEventKind,
    normalize_received_message_uuid_for_lifecycle,
    record_user_signed_on,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.companion.scope import CompanionScope
from app.schemas.chat import UserTimeContext
from app.schemas.chat_websocket import (
    ChatWsUserSignedOnFrame,
    local_ts_and_timezone_from_ws_time_context,
)


def test_local_ts_and_timezone_from_ws_time_context() -> None:
    utc = UserTimeContext(
        local_time="2026-05-17T10:30:00+08:00",
        timezone="Asia/Shanghai",
        utc_offset_minutes=480,
    )
    resolved = local_ts_and_timezone_from_ws_time_context(utc)
    assert resolved == ("2026-05-17T10:30:00+08:00", "Asia/Shanghai")


def test_chat_ws_user_signed_on_frame_requires_non_empty_local_time() -> None:
    with pytest.raises(ValidationError):
        ChatWsUserSignedOnFrame.model_validate(
            {
                "type": "user_signed_on",
                "agent_id": "agent-1",
                "message_id": "11111111-2222-4333-8444-555555555555",
                "time_context": {
                    "local_time": "   ",
                    "timezone": "Asia/Shanghai",
                },
            }
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
        chat_id="1bcb5cfa-b11a-48cd-8903-c227a1a890a5",
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
    assert row["chat_id"] == "1bcb5cfa-b11a-48cd-8903-c227a1a890a5"
    assert row["received_message_uuid"] == "11111111-2222-4333-8444-555555555555"


def test_normalize_received_message_uuid_for_lifecycle() -> None:
    assert normalize_received_message_uuid_for_lifecycle("") == "-"
    assert (
        normalize_received_message_uuid_for_lifecycle("aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee")
        == "aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee"
    )
