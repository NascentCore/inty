from __future__ import annotations

import json

from app.core.companion_harness.companion.bgm_library import (
    SET_BGM_OK_PREFIX,
    SET_BGM_TOOL_NAME,
    extract_set_bgm_deliver_payload,
)


def test_extract_set_bgm_deliver_payload_ok() -> None:
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
        {"role": "tool", "tool_call_id": "tc1", "content": SET_BGM_OK_PREFIX + json.dumps(payload)},
    ]
    parsed = extract_set_bgm_deliver_payload(msgs)
    assert parsed is not None
    assert parsed["track_id"] == "calm_evening_01"


def test_extract_set_bgm_deliver_payload_error_returns_none() -> None:
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
    assert extract_set_bgm_deliver_payload(msgs) is None
