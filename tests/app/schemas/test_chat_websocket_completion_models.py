"""Schema tests for companion WS downlink completion wire models (Phase 1)."""

from __future__ import annotations

from typing import Any

import pytest

from app.core.companion_harness.companion.inner_tick_kind import InnerTickKind
from app.schemas.chat_websocket import (
    ChatWebSocketQueuedSuccessFrame,
    ChatWsCompanionWireMessageMetaData,
    ChatWsCompletionData,
    build_inner_tick_wire_meta,
    dump_chat_ws_companion_wire_meta,
)


def _base_completion_data(meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "chatcmpl-abc123def456",
        "object": "chat.completion",
        "created": 1716780000,
        "model": "chatbot",
        "user_message_id": 42,
        "localId": "client-opt-id-1",
        "business_actions": [{"action_type": "none", "message": ""}],
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": "companion-ws-reply",
                    "id": 905,
                    "timestamp": "2026-05-27T02:00:00+00:00",
                    "audio_url": None,
                    "meta_data": meta,
                },
            }
        ],
        "usage": {
            "prompt_tokens": 1,
            "completion_tokens": 2,
            "total_tokens": 3,
        },
    }


def _queued_success_frame(meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": 200,
        "message": "success",
        "data": _base_completion_data(meta),
        "agent_id": "agent-uuid",
        "status_line": "Online",
    }


FOREGROUND_CHAT_META = {
    "source": "chat",
    "user_msg_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "assistant_msg_uuid": "33333333-3333-4333-8333-000000000002",
    "tool_background_started": True,
    "significance_perception": {
        "importance_round": 9,
        "importance_user_message": 8,
        "importance_assistant_message": 7,
    },
}

TOOL_BG_META = {
    "source": "tool_bg",
    "reply_to_user_msg_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "tool_bg_output_to_user": True,
    "generated_image": {
        "image_url": "https://example.com/img.png",
        "width": 512,
        "height": 512,
    },
    "significance_perception": {"importance_round": 5},
}

BOOTSTRAP_INTERIM_META = {
    "source": "bootstrap_tool_round",
    "bootstrapRoundIndex": 2,
    "user_msg_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "assistant_msg_uuid": "33333333-3333-4333-8333-000000000002",
}

INNER_TICK_META = {
    "source": "inner_tick",
    "inner_tick_activity": "proactive_chat",
    "companion_proactive_chat": True,
    "inner_tick": True,
    "proactive_chat": True,
}


@pytest.mark.parametrize(
    "meta",
    [
        FOREGROUND_CHAT_META,
        TOOL_BG_META,
        BOOTSTRAP_INTERIM_META,
        INNER_TICK_META,
    ],
)
def test_chat_websocket_queued_success_frame_model_validate(
    meta: dict[str, Any],
) -> None:
    frame = ChatWebSocketQueuedSuccessFrame.model_validate(
        _queued_success_frame(meta)
    )
    assert frame.code == 200
    assert frame.agent_id == "agent-uuid"
    assert frame.status_line == "Online"
    choice0 = frame.data.choices[0]
    assert choice0.index == 0
    assert choice0.finish_reason == "stop"
    msg = choice0.message
    assert msg.role == "assistant"
    assert msg.content == "companion-ws-reply"
    assert msg.id == 905
    assert msg.meta_data is not None
    assert msg.meta_data.source == meta["source"]
    assert frame.data.local_id == "client-opt-id-1"


def test_chat_websocket_queued_success_frame_round_trip_dump() -> None:
    frame = ChatWebSocketQueuedSuccessFrame.model_validate(
        _queued_success_frame(FOREGROUND_CHAT_META)
    )
    dumped = frame.model_dump(exclude_none=True, by_alias=True)
    round_trip = ChatWebSocketQueuedSuccessFrame.model_validate(dumped)
    assert round_trip == frame


def test_chat_ws_completion_data_nested_meta_typing() -> None:
    data = ChatWsCompletionData.model_validate(
        _base_completion_data(TOOL_BG_META)
    )
    meta = data.choices[0].message.meta_data
    assert meta is not None
    assert meta.generated_image is not None
    assert meta.generated_image.image_url == "https://example.com/img.png"
    assert meta.significance_perception is not None
    assert meta.significance_perception.importance_round == 5
    assert meta.significance_perception.importance_user_message is None


def test_chat_ws_companion_wire_meta_partial_significance() -> None:
    meta = ChatWsCompanionWireMessageMetaData.model_validate(
        {"significance_perception": {"importance_round": 7}}
    )
    assert meta.significance_perception is not None
    assert meta.significance_perception.importance_round == 7


def test_chat_ws_companion_wire_meta_monolog_round_trip_and_legacy_input() -> (
    None
):
    meta = ChatWsCompanionWireMessageMetaData(
        inner_tick=True,
        companion_monolog_inner_tick=True,
    )
    dumped = dump_chat_ws_companion_wire_meta(meta)
    assert dumped == {
        "inner_tick": True,
        "companionMonologInnerTick": True,
    }

    legacy = ChatWsCompanionWireMessageMetaData.model_validate(
        {
            "inner_tick": True,
            "companion_maintenance_inner_tick": True,
        }
    )
    assert legacy.companion_monolog_inner_tick is True
    assert dump_chat_ws_companion_wire_meta(legacy) == dumped


def test_build_inner_tick_wire_meta_monolog_matches_literal() -> None:
    built = build_inner_tick_wire_meta(InnerTickKind.MONOLOG)
    literal = ChatWsCompanionWireMessageMetaData(
        inner_tick=True,
        companion_monolog_inner_tick=True,
    )
    assert dump_chat_ws_companion_wire_meta(
        built
    ) == dump_chat_ws_companion_wire_meta(literal)


def test_build_inner_tick_wire_meta_proactive_matches_literal() -> None:
    built = build_inner_tick_wire_meta(InnerTickKind.PROACTIVE_CHAT)
    literal = ChatWsCompanionWireMessageMetaData(
        inner_tick=True,
        proactive_chat=True,
        companion_proactive_chat=True,
    )
    assert dump_chat_ws_companion_wire_meta(
        built
    ) == dump_chat_ws_companion_wire_meta(literal)


def test_build_inner_tick_wire_meta_scheduled_matches_literal() -> None:
    built = build_inner_tick_wire_meta(
        InnerTickKind.SCHEDULED,
        scheduled_task_id="task-42",
    )
    literal = ChatWsCompanionWireMessageMetaData(
        inner_tick=True,
        companion_scheduled_reminder=True,
        scheduled_task_id="task-42",
    )
    assert dump_chat_ws_companion_wire_meta(
        built
    ) == dump_chat_ws_companion_wire_meta(literal)


def test_build_inner_tick_wire_meta_autonomy_raises() -> None:
    with pytest.raises(ValueError, match="autonomy inner tick"):
        build_inner_tick_wire_meta(InnerTickKind.AUTONOMY)


def test_build_chat_ws_queued_success_frame_round_trip() -> None:
    from app.services.chat_completion_wire import (
        build_chat_ws_queued_success_frame,
    )

    completion = ChatWsCompletionData.model_validate(
        _base_completion_data(FOREGROUND_CHAT_META)
    )
    frame = build_chat_ws_queued_success_frame(
        completion=completion,
        agent_id="agent-uuid",
        status_line="Online",
    )
    round_trip = ChatWebSocketQueuedSuccessFrame.model_validate(
        frame.model_dump(exclude_none=True)
    )
    assert round_trip.agent_id == "agent-uuid"
    assert round_trip.status_line == "Online"
    assert round_trip.data.id == completion.id
