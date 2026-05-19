from __future__ import annotations

import json

from app.core.companion_harness.companion.bgm_library import (
    SET_BGM_OK_PREFIX,
    SET_BGM_TOOL_NAME,
    SetBgmDeliverPayload,
    parse_set_bgm_ok_tool_content,
    set_bgm_deliver_from_appended_turn,
)


def test_parse_set_bgm_ok_tool_content() -> None:
    payload = SetBgmDeliverPayload(
        track_id="calm_evening_01",
        title="Calm",
        audio_url="https://cdn.example.com/x.mp3",
        duration_sec=180.0,
        tags=["calm"],
        reason="test",
    )
    parsed = parse_set_bgm_ok_tool_content(SET_BGM_OK_PREFIX + payload.model_dump_json())
    assert parsed == payload


def test_set_bgm_deliver_from_appended_turn_ok() -> None:
    payload = {"track_id": "calm_evening_01", "title": "Calm", "reason": "test"}
    msgs = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "tc1",
                    "function": {"name": SET_BGM_TOOL_NAME, "arguments": "{}"},
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "tc1",
            "content": SET_BGM_OK_PREFIX
            + json.dumps(
                {
                    **payload,
                    "audio_url": "https://cdn.example.com/x.mp3",
                    "duration_sec": 180.0,
                    "tags": [],
                }
            ),
        },
    ]
    parsed = set_bgm_deliver_from_appended_turn(msgs)
    assert parsed is not None
    assert parsed.track_id == "calm_evening_01"


def test_set_bgm_deliver_from_appended_turn_error_returns_none() -> None:
    msgs = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "tc1",
                    "function": {"name": SET_BGM_TOOL_NAME, "arguments": "{}"},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "tc1", "content": "ERROR: unknown track_id"},
    ]
    assert set_bgm_deliver_from_appended_turn(msgs) is None
