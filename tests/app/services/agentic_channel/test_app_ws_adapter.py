"""Tests for stateless AppWsChannelAdapter downlink materialization."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.output_queue import (
    OutputDeliveryUnroutableError,
    ReadyOutputMessage,
)
from app.core.companion_harness.agentic_companion.types import (
    InputQueueRecord,
    QueueStatus,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)
from app.core.companion_harness.tools.tool_background import ToolOutputEvent
from app.services.agentic_channel.adapters.app_ws import AppWsChannelAdapter
from app.services.agentic_channel.channel_runtime import (
    ChannelRuntimeState,
    clear_registries_for_tests,
    get_scope_channel_registry,
)
from app.services.agentic_channel.presence import (
    AgentChannelPresence,
    clear_presences_for_tests,
)
from app.services.agentic_companion.downlink import (
    Downlink,
    DownlinkKind,
    queue_user_reply_downlink,
)


@pytest.fixture(autouse=True)
def _clear_channel_registries() -> None:
    clear_presences_for_tests()
    clear_registries_for_tests()


class _SessionContext:
    async def __aenter__(self):
        return AsyncMock()

    async def __aexit__(self, exc_type, exc, tb):
        return None


def _input_record(
    scope: AgentScope,
    message_id: str,
    *,
    text: str = "hi",
    local_id: str | None = "local-1",
    chat_history_user_row_id: int | None = 101,
) -> InputQueueRecord:
    return InputQueueRecord(
        message_id=message_id,
        scope=scope,
        sequence=1,
        status=QueueStatus.DELIVERED,
        channel=ChannelKind.APP_WS,
        wire_id="app:ws",
        text=text,
        received_at_utc=datetime.now(timezone.utc),
        client_message_id=message_id,
        local_id=local_id,
        chat_history_user_row_id=chat_history_user_row_id,
        batch_id="batch-1",
    )


@pytest.mark.asyncio
async def test_app_ws_user_reply_materializes_from_durable_rows() -> None:
    scope = AgentScope(user_id="user-app-ws", agent_id="agent-app-ws")
    outbound_queue: asyncio.Queue = asyncio.Queue()
    adapter = AppWsChannelAdapter(scope=scope, outbound_queue=outbound_queue)
    ready = ReadyOutputMessage(
        message_id="out-1",
        batch_id="batch-1",
        kind=DownlinkKind.USER_REPLY,
        text="hello queue",
        sequence=1,
        message_ids=("client-msg-1",),
    )
    input_records = (_input_record(scope, "client-msg-1"),)
    repo = SimpleNamespace(
        get_records_by_ids=AsyncMock(return_value=input_records)
    )
    expected_payload = {
        "code": 200,
        "agent_id": scope.agent_id,
        "data": {"choices": [{"message": {"content": "hello queue"}}]},
    }

    with (
        patch(
            "app.services.agentic_channel.adapters.app_ws.AsyncSessionLocal",
            return_value=_SessionContext(),
        ),
        patch(
            "app.services.agentic_channel.adapters.app_ws.PostgresInputQueueRepository",
            return_value=repo,
        ),
        patch(
            "app.services.agentic_channel.adapters.app_ws.materialize_queue_user_reply_from_durable",
            new_callable=AsyncMock,
            return_value=expected_payload,
        ) as materialize,
    ):
        await adapter.as_downlink().deliver(
            queue_user_reply_downlink(
                assistant_text=ready.text,
                message_ids=ready.message_ids,
                output_message=ready,
            )
        )

    materialize.assert_awaited_once()
    call = materialize.await_args.kwargs
    assert call["scope"] == scope
    assert call["message"] == ready
    assert call["input_records"] == input_records
    assert await outbound_queue.get() == expected_payload


@pytest.mark.asyncio
async def test_app_ws_user_reply_missing_input_is_unroutable() -> None:
    scope = AgentScope(user_id="user-missing", agent_id="agent-missing")
    adapter = AppWsChannelAdapter(scope=scope, outbound_queue=asyncio.Queue())
    ready = ReadyOutputMessage(
        message_id="out-missing",
        batch_id="batch-missing",
        kind=DownlinkKind.USER_REPLY,
        text="reply",
        sequence=1,
        message_ids=("missing-input",),
    )
    repo = SimpleNamespace(get_records_by_ids=AsyncMock(return_value=()))

    with (
        patch(
            "app.services.agentic_channel.adapters.app_ws.AsyncSessionLocal",
            return_value=_SessionContext(),
        ),
        patch(
            "app.services.agentic_channel.adapters.app_ws.PostgresInputQueueRepository",
            return_value=repo,
        ),
        pytest.raises(OutputDeliveryUnroutableError),
    ):
        await adapter.as_downlink().deliver(
            queue_user_reply_downlink(
                assistant_text=ready.text,
                message_ids=ready.message_ids,
                output_message=ready,
            )
        )


@pytest.mark.asyncio
async def test_app_ws_tool_background_uses_input_row_user_message_id() -> None:
    scope = AgentScope(user_id="user-tb", agent_id="agent-tb")
    outbound_queue: asyncio.Queue = asyncio.Queue()
    adapter = AppWsChannelAdapter(scope=scope, outbound_queue=outbound_queue)
    input_records = (
        _input_record(
            scope,
            "user-msg-uuid",
            local_id="local-tb",
            chat_history_user_row_id=55,
        ),
    )
    repo = SimpleNamespace(
        get_records_by_ids=AsyncMock(return_value=input_records)
    )
    ev = ToolOutputEvent(
        scope_registry_key=scope.registry_key(),
        memory_store=SimpleNamespace(),
        user_msg_uuid="user-msg-uuid",
        assistant_msg_uuid="assist-uuid",
        text="tool bg line",
        ts="2025-01-01T00:00:00Z",
        elapsed_ms=1,
        trace_id="trace-1",
        langsmith_trace_id="ls-trace",
        langsmith_run_id="ls-run",
        output_to_user=True,
        generation_deliver=False,
        image_asset_baseline=0,
        local_image_paths=(),
        significance_perception={},
        turn_recall=None,
        inner_tick_activity=None,
    )
    expected_payload = {"code": 200, "agent_id": scope.agent_id}

    with (
        patch(
            "app.services.agentic_channel.adapters.app_ws.AsyncSessionLocal",
            return_value=_SessionContext(),
        ),
        patch(
            "app.services.agentic_channel.adapters.app_ws.PostgresInputQueueRepository",
            return_value=repo,
        ),
        patch(
            "app.services.agentic_channel.adapters.app_ws.materialize_tool_background_ws_payload",
            new_callable=AsyncMock,
            return_value=expected_payload,
        ) as materialize,
    ):
        await adapter.as_downlink().deliver(
            Downlink(
                kind=DownlinkKind.TOOL_BACKGROUND,
                assistant_text="tool bg line",
                turn=None,
                tool_output=ev,
                bootstrap_interim=None,
                scheduled_task_id=None,
                transcript_user_text=None,
            )
        )

    call = materialize.await_args.kwargs
    assert call["effective_local_id"] == "local-tb"
    assert call["foreground_user_message_id"] == 55
    assert await outbound_queue.get() == expected_payload


@pytest.mark.asyncio
async def test_presence_deliver_ready_passes_ready_message_to_app_adapter() -> (
    None
):
    scope = AgentScope(user_id="user-pres-app", agent_id="agent-pres-app")
    outbound_queue: asyncio.Queue = asyncio.Queue()
    adapter = AppWsChannelAdapter(scope=scope, outbound_queue=outbound_queue)
    downlink = adapter.as_downlink()
    registry = get_scope_channel_registry(scope)
    registry.states[ChannelKind.APP_WS] = ChannelRuntimeState.ACTIVE
    registry.adapters[ChannelKind.APP_WS] = adapter
    registry.downlinks[ChannelKind.APP_WS] = downlink
    presence = AgentChannelPresence(scope)
    ready = ReadyOutputMessage(
        message_id="out-redeliver",
        batch_id="batch-redeliver",
        kind=DownlinkKind.USER_REPLY,
        text="redelivered reply",
        sequence=1,
        message_ids=("client-msg-redelivery",),
    )

    with patch.object(
        downlink,
        "deliver",
        new_callable=AsyncMock,
    ) as deliver:
        await presence._deliver_ready_via_active_channel(ready)

    delivered = deliver.await_args.args[0]
    assert delivered.output_message == ready
