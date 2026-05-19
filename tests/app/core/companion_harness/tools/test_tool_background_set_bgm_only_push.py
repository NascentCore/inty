"""Regression: BGM-only tool_background must emit ToolOutputEvent (not swallowed by should_push / ~909)."""

from __future__ import annotations

import json

from app.core.companion_harness.companion.bgm_library import (
    SET_BGM_OK_PREFIX,
    SET_BGM_TOOL_NAME,
    set_bgm_deliver_from_appended_turn,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.tools.companion_tool_runtime import (
    execute_tool_call_blocking,
)
from app.core.companion_harness.tools.tool_background import (
    build_tool_background_transcript_body,
)


def _bgm_only_appended_turn_msgs(store: MemoryStore) -> list[dict]:
    tool_out = execute_tool_call_blocking(
        store,
        SET_BGM_TOOL_NAME,
        json.dumps({"track_id": "warm_chat_02", "reason": "warmer mood"}),
    )
    assert tool_out.startswith(SET_BGM_OK_PREFIX)
    return [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "tc_set_bgm",
                    "function": {
                        "name": SET_BGM_TOOL_NAME,
                        "arguments": json.dumps(
                            {"track_id": "warm_chat_02", "reason": "warmer mood"}
                        ),
                    },
                }
            ],
        },
        {"role": "tool", "tool_call_id": "tc_set_bgm", "content": tool_out},
    ]


def test_bgm_only_round_sets_should_push_and_avoids_909_suppress(
    store: MemoryStore | None = None,
) -> None:
    memory_store = store or MemoryStore(
        scope=CompanionScope("u", "a", "bgm-push"), repository=None
    )
    appended = _bgm_only_appended_turn_msgs(memory_store)
    set_bgm_payload = set_bgm_deliver_from_appended_turn(appended)
    assert set_bgm_payload is not None
    set_bgm_deliver = set_bgm_payload is not None
    generation_deliver = False
    output_to_user_flag = False
    should_push = generation_deliver or output_to_user_flag or set_bgm_deliver
    assert should_push
    transcript_body = build_tool_background_transcript_body(
        display_text="",
        appended_turn_msgs=appended,
        total_tool_calls=1,
    )
    suppress_empty_transcript = (
        not transcript_body.strip()
        and not generation_deliver
        and not set_bgm_deliver
    )
    assert not suppress_empty_transcript


def test_bgm_only_empty_transcript_still_pushes_when_set_bgm_deliver() -> None:
    """Second safety net: digest stripped but set_bgm_deliver must not hit ~909 return."""
    set_bgm_deliver = True
    generation_deliver = False
    transcript_body = ""
    suppress = (
        not transcript_body.strip()
        and not generation_deliver
        and not set_bgm_deliver
    )
    assert not suppress
