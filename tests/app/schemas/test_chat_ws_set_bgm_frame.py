from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.chat_websocket import ChatWsSetBgmFrame


def test_chat_ws_set_bgm_frame_roundtrip() -> None:
    frame = ChatWsSetBgmFrame(
        agent_id="agent-1",
        user_msg_uuid="550e8400-e29b-41d4-a716-446655440000",
        trace_id="trace-1",
        track_id="calm_evening_01",
        title="Calm Evening",
        audio_url="https://cdn.example.com/bgm/calm_evening_01.mp3",
        duration_sec=180.0,
        tags=["calm"],
        reason="mood",
        user_message_id=42,
    )
    dumped = frame.model_dump(exclude_none=True)
    assert dumped["type"] == "set_bgm"
    assert dumped["user_msg_uuid"] == "550e8400-e29b-41d4-a716-446655440000"
    assert dumped["user_message_id"] == 42


def test_chat_ws_set_bgm_frame_requires_user_msg_uuid() -> None:
    with pytest.raises(ValidationError):
        ChatWsSetBgmFrame(
            agent_id="a",
            user_msg_uuid="",
            track_id="t",
            title="T",
            audio_url="https://example.com/x.mp3",
            duration_sec=1.0,
            reason="r",
        )
