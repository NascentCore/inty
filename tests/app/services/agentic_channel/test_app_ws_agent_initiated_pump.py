"""Parity tests for App-WS agent-initiated OutputQueue delivery (#3543 / #3576)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.output_queue import (
    ReadyOutputMessage,
)
from app.core.companion_harness.companion.models import CompanionTurnResult
from app.core.companion_harness.companion.runtime_channel import ChannelKind
from app.schemas.chat_websocket import ChatWsCompanionWireMessageMetaData
from app.services.agentic_channel.adapters.app_ws import AppWsChannelAdapter
from app.services.agentic_companion.downlink import DownlinkKind
from app.services.agentic_companion.inner_tick_deliver import (
    InnerTickVisibleDeliverInput,
    deliver_visible_inner_tick_turn,
)
from app.services.agentic_companion.inner_tick_delivery import (
    inner_tick_delivery_for_pump_owned,
)


class _SessionContext:
    async def __aenter__(self):
        return AsyncMock()

    async def __aexit__(self, exc_type, exc, tb):
        return None


def _choices_text(payload) -> str:
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump()
    data = payload.get("data")
    assert isinstance(data, dict)
    choices = data.get("choices")
    assert isinstance(choices, list) and choices
    message = choices[0].get("message")
    assert isinstance(message, dict)
    content = message.get("content")
    assert isinstance(content, str)
    return content


@pytest.mark.asyncio
async def test_proactive_kind_delivers_via_adapter() -> None:
    scope = AgentScope(user_id="user-parity-pro", agent_id="agent-parity-pro")
    assistant_text = "proactive hello from Inty"
    pump_queue: asyncio.Queue = asyncio.Queue()
    ready = ReadyOutputMessage(
        message_id="out-pro-1",
        batch_id="agent-initiated:proactive",
        kind=DownlinkKind.PROACTIVE,
        text=assistant_text,
        sequence=1,
        message_ids=(),
    )
    latest_ai_info = {"meta_data": {"source": "proactive"}}
    adapter = AppWsChannelAdapter(scope=scope, outbound_queue=pump_queue)

    with (
        patch(
            "app.services.agentic_channel.adapters.app_ws.AsyncSessionLocal",
            return_value=_SessionContext(),
        ),
        patch(
            "app.services.agentic_companion.ws_outbound_materialize."
            "resolve_chat_model_for_scope",
            new=AsyncMock(
                return_value=SimpleNamespace(id_on_provider="test-model")
            ),
        ),
        patch(
            "app.services.agentic_companion.ws_outbound_materialize."
            "chat_history_service.get_latest_ai_message_info",
            new=AsyncMock(return_value=latest_ai_info),
        ),
        patch(
            "app.services.agentic_companion.ws_outbound_materialize."
            "chat_history_service.get_latest_user_message_id",
            new=AsyncMock(return_value=88),
        ),
        patch(
            "app.services.agentic_companion.ws_outbound_materialize."
            "agent_status_line_for_chat_header",
            new=AsyncMock(return_value="status"),
        ),
    ):
        await adapter.as_downlink().deliver(ready)

    pump_payload = await pump_queue.get()
    assert _choices_text(pump_payload) == assistant_text
    dumped = (
        pump_payload.model_dump()
        if hasattr(pump_payload, "model_dump")
        else pump_payload
    )
    assert dumped["agent_id"] == scope.agent_id


@pytest.mark.asyncio
async def test_greeting_agent_initiated_user_reply_kind_via_adapter() -> None:
    scope = AgentScope(
        user_id="user-parity-greet", agent_id="agent-parity-greet"
    )
    greeting_text = "Hello from Inty on sign-on."
    outbound_queue: asyncio.Queue = asyncio.Queue()
    adapter = AppWsChannelAdapter(scope=scope, outbound_queue=outbound_queue)
    ready = ReadyOutputMessage(
        message_id="out-greet-parity",
        batch_id="agent-initiated:greeting",
        kind=DownlinkKind.USER_REPLY,
        text=greeting_text,
        sequence=1,
        message_ids=(),
    )
    latest_ai_info = {"meta_data": {"source": "greeting"}}

    with (
        patch(
            "app.services.agentic_channel.adapters.app_ws.AsyncSessionLocal",
            return_value=_SessionContext(),
        ),
        patch(
            "app.services.agentic_companion.ws_outbound_materialize."
            "resolve_chat_model_for_scope",
            new=AsyncMock(
                return_value=SimpleNamespace(id_on_provider="test-model")
            ),
        ),
        patch(
            "app.services.agentic_companion.ws_outbound_materialize."
            "chat_history_service.get_latest_ai_message_info",
            new=AsyncMock(return_value=latest_ai_info),
        ),
        patch(
            "app.services.agentic_companion.ws_outbound_materialize."
            "chat_history_service.get_latest_user_message_id",
            new=AsyncMock(return_value=42),
        ),
        patch(
            "app.services.agentic_companion.ws_outbound_materialize."
            "agent_status_line_for_chat_header",
            new=AsyncMock(return_value="status"),
        ),
    ):
        await adapter.as_downlink().deliver(ready)

    payload = await outbound_queue.get()
    assert _choices_text(payload) == greeting_text
    dumped = payload.model_dump() if hasattr(payload, "model_dump") else payload
    assert dumped["agent_id"] == scope.agent_id


@pytest.mark.asyncio
async def test_agent_initiated_materialize_tolerates_missing_ai_row() -> None:
    scope = AgentScope(user_id="user-race", agent_id="agent-race")
    outbound_queue: asyncio.Queue = asyncio.Queue()
    adapter = AppWsChannelAdapter(scope=scope, outbound_queue=outbound_queue)
    ready = ReadyOutputMessage(
        message_id="out-race",
        batch_id="agent-initiated:race",
        kind=DownlinkKind.PROACTIVE,
        text="race-safe proactive",
        sequence=1,
        message_ids=(),
    )

    with (
        patch(
            "app.services.agentic_channel.adapters.app_ws.AsyncSessionLocal",
            return_value=_SessionContext(),
        ),
        patch(
            "app.services.agentic_companion.ws_outbound_materialize."
            "resolve_chat_model_for_scope",
            new=AsyncMock(
                return_value=SimpleNamespace(id_on_provider="test-model")
            ),
        ),
        patch(
            "app.services.agentic_companion.ws_outbound_materialize."
            "chat_history_service.get_latest_ai_message_info",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.services.agentic_companion.ws_outbound_materialize."
            "chat_history_service.get_latest_user_message_id",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.services.agentic_companion.ws_outbound_materialize."
            "agent_status_line_for_chat_header",
            new=AsyncMock(return_value="status"),
        ),
    ):
        await adapter.as_downlink().deliver(ready)

    payload = await outbound_queue.get()
    assert _choices_text(payload) == ready.text


@pytest.mark.asyncio
async def test_app_ws_skips_direct_send_when_output_queue_rows_exist() -> None:
    pump_owned = inner_tick_delivery_for_pump_owned(ChannelKind.APP_WS)
    with (
        patch(
            "app.services.agentic_companion.inner_tick_deliver."
            "chat_history_service.add_ai_message_sync_async",
            new=AsyncMock(return_value=301),
        ) as add_ai,
        patch(
            "app.services.agentic_companion.inner_tick_deliver."
            "deliver_inner_tick_assistant",
            new=AsyncMock(),
        ) as channel_send,
    ):
        delivered = await deliver_visible_inner_tick_turn(
            InnerTickVisibleDeliverInput(
                delivery=pump_owned,
                session_id="session-app-ws",
                chat_row_agent_id="agent-1",
                preset_uid="uid-1",
                transcript_user_text="[proactive]",
                companion_turn=CompanionTurnResult(
                    assistant_text="hello pump",
                    output_message_ids=("out-app-ws",),
                ),
                user_wire_meta=ChatWsCompanionWireMessageMetaData(
                    source="proactive"
                ),
                companion_scheduled_reminder=None,
                scheduled_task_id=None,
                log_label="app_ws_pump_owned",
                skip_user_history=True,
            )
        )
    assert delivered is True
    add_ai.assert_awaited_once()
    channel_send.assert_not_awaited()
