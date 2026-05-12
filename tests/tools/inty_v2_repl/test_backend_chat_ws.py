"""Narrow contract tests for ``tools.inty_v2_repl.backend_chat_ws`` (uplink/downlink helpers)."""

from __future__ import annotations

import json

import pytest

from tools.inty_v2_repl.backend_chat_ws import (
    BackendChatWsError,
    build_ws_user_time_context_now,
    http_base_to_ws_chat_url,
    parse_chat_completion_ws_payload,
    _ws_chat_turn_send_payload,
)


def test_http_base_to_ws_chat_url() -> None:
    assert (
        http_base_to_ws_chat_url("http://127.0.0.1:8000/")
        == "ws://127.0.0.1:8000/api/v1/chat/ws"
    )
    assert (
        http_base_to_ws_chat_url("https://example.com")
        == "wss://example.com/api/v1/chat/ws"
    )


def test_parse_chat_response_payload_success() -> None:
    data = {
        "code": 200,
        "message": "success",
        "data": {
            "choices": [
                {
                    "message": {
                        "content": "hello",
                        "meta_data": {"source": "chat"},
                    }
                }
            ]
        },
        "agent_id": "agent-1",
    }
    text, meta = parse_chat_completion_ws_payload(data)
    assert text == "hello"
    assert meta == {"source": "chat"}


def test_parse_chat_response_payload_error() -> None:
    with pytest.raises(BackendChatWsError) as exc_info:
        parse_chat_completion_ws_payload(
            {"code": 400, "message": "No user message found", "agent_id": "a"}
        )
    assert exc_info.value.code == 400
    assert "user" in exc_info.value.agent_message.lower()


def test_build_ws_user_time_context_now_shape() -> None:
    ctx = build_ws_user_time_context_now()
    assert ctx.local_time and str(ctx.local_time).strip()
    assert isinstance(ctx.utc_offset_minutes, int)


def test_build_ws_user_time_context_now_tz_utc(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TZ", "UTC")
    ctx = build_ws_user_time_context_now()
    assert ctx.timezone == "UTC"
    assert ctx.utc_offset_minutes == 0


def test_ws_chat_turn_send_payload_includes_time_context() -> None:
    mid, raw = _ws_chat_turn_send_payload(
        "aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee",
        "hello",
        "bbbbbbbb-bbbb-4ccc-dddd-eeeeeeeeeeee",
    )
    assert mid == "bbbbbbbb-bbbb-4ccc-dddd-eeeeeeeeeeee"
    outer = json.loads(raw)
    tc = outer["request"]["time_context"]
    assert isinstance(tc["local_time"], str) and tc["local_time"]
    assert isinstance(tc["utc_offset_minutes"], int)
