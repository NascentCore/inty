"""Tests for companion WS completion wire builder (issue #3208)."""

from __future__ import annotations

from app.schemas.biz_action import ActionType, BizAction
from app.schemas.chat import ChatCompletionRequest
from app.schemas.chat_websocket import ChatWebSocketQueuedSuccessFrame, ChatWsCompletionData
from app.services.chat_completion_wire import build_companion_ws_completion_data


def test_build_companion_ws_completion_data_validates_as_typed_frame() -> None:
    request = ChatCompletionRequest(
        model="chatbot",
        messages=[{"role": "user", "content": "hi"}],
    )
    meta = {
        "source": "chat",
        "user_msg_uuid": "550e8400-e29b-41d4-a716-446655440000",
    }
    completion = build_companion_ws_completion_data(
        response_text_content="hello",
        response_content_parts=None,
        last_user_text="hi",
        latest_message_info={
            "id": 905,
            "meta_data": meta,
            "timestamp": "2026-05-27T02:00:00+00:00",
            "audio_url": None,
        },
        audio_url=None,
        request=request,
        source_imate_id=None,
        user_message_id=42,
        subscription_actions=[BizAction(action_type=ActionType.NONE, message="")],
        client_local_id="client-opt-id-1",
    )
    assert isinstance(completion, ChatWsCompletionData)
    frame = ChatWebSocketQueuedSuccessFrame.model_validate(
        {
            "code": 200,
            "message": "success",
            "data": completion.model_dump(exclude_none=True),
            "agent_id": "agent-uuid",
            "status_line": "Online",
        }
    )
    assert frame.data.choices[0].message.content == "hello"
    assert frame.data.user_message_id == 42
