"""Contract helpers for inty v2 prototype backend WebSocket client."""

from __future__ import annotations

import pytest

from tools.inty_v2_repl.backend_chat_ws import (
    BackendChatWsError,
    _parse_chat_response_payload,
    http_base_to_ws_chat_url,
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
    text, meta = _parse_chat_response_payload(data)
    assert text == "hello"
    assert meta == {"source": "chat"}


def test_parse_chat_response_payload_error() -> None:
    with pytest.raises(BackendChatWsError) as exc_info:
        _parse_chat_response_payload(
            {"code": 400, "message": "No user message found", "agent_id": "a"}
        )
    assert exc_info.value.code == 400
    assert "user" in exc_info.value.agent_message.lower()
