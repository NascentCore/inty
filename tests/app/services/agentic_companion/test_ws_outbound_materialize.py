"""Tests for durable App-WS outbound materialization."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.output_queue import (
    ReadyOutputMessage,
)
from app.core.companion_harness.agentic_companion.types import (
    GeneratedImageRef,
    InputQueueRecord,
    QueueStatus,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)
from app.services.agentic_companion.downlink import DownlinkKind
from app.schemas.chat_websocket import ChatWebSocketQueuedSuccessFrame
from app.services.agentic_companion.ws_outbound_materialize import (
    materialize_queue_user_reply_from_durable,
)


def _input_record(scope: AgentScope) -> InputQueueRecord:
    return InputQueueRecord(
        message_id="client-msg-1",
        scope=scope,
        sequence=1,
        status=QueueStatus.DELIVERED,
        channel=ChannelKind.APP_WS,
        wire_id="app:ws",
        text="hi there",
        received_at_utc=datetime.now(timezone.utc),
        client_message_id="client-msg-1",
        local_id="local-bubble-1",
        chat_history_user_row_id=101,
        batch_id="batch-1",
    )


@pytest.mark.asyncio
async def test_materialize_queue_user_reply_from_durable_wire_fields() -> None:
    scope = AgentScope(user_id="user-mat", agent_id="agent-mat")
    ready = ReadyOutputMessage(
        message_id="out-1",
        batch_id="batch-1",
        kind=DownlinkKind.USER_REPLY,
        text="hello durable",
        sequence=1,
        message_ids=("client-msg-1",),
        tool_background_started=True,
        generated_images=(
            GeneratedImageRef(
                image_url="gs://bucket/image.png",
                width=512,
                height=512,
            ),
        ),
    )
    db = AsyncMock()
    model = SimpleNamespace(id_on_provider="test/chat-model")

    with (
        patch(
            "app.services.agentic_companion.ws_outbound_materialize.resolve_chat_model_for_scope",
            new_callable=AsyncMock,
            return_value=model,
        ),
        patch(
            "app.services.agentic_companion.ws_outbound_materialize.chat_history_service.add_ai_message_sync_async",
            new_callable=AsyncMock,
            return_value=202,
        ),
        patch(
            "app.services.agentic_companion.ws_outbound_materialize.chat_history_service.get_ai_message_info_by_id",
            new_callable=AsyncMock,
            return_value={
                "id": 202,
                "meta_data": {
                    "source": "chat",
                    "user_msg_uuid": "client-msg-1",
                    "tool_background_started": True,
                    "generated_image": {
                        "image_url": "gs://bucket/image.png",
                        "width": 512,
                        "height": 512,
                    },
                },
                "timestamp": "2025-01-01T00:00:00+00:00",
                "audio_url": None,
            },
        ),
        patch(
            "app.services.agentic_companion.ws_outbound_materialize.agent_status_line_for_chat_header",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        payload = await materialize_queue_user_reply_from_durable(
            db=db,
            scope=scope,
            message=ready,
            input_records=(_input_record(scope),),
        )

    assert isinstance(payload, ChatWebSocketQueuedSuccessFrame)
    assert payload.code == 200
    assert payload.agent_id == scope.agent_id
    data = payload.data
    assert data.local_id == "local-bubble-1"
    assert data.model == "test/chat-model"
    assert data.source_imate_id == scope.agent_id
    assert data.user_message_id == 101
    assert data.usage is None
    meta = data.choices[0].message.meta_data
    assert meta is not None
    assert meta.user_msg_uuid == "client-msg-1"
    assert meta.tool_background_started is True
    assert meta.generated_image is not None
    assert meta.generated_image.image_url == "gs://bucket/image.png"
