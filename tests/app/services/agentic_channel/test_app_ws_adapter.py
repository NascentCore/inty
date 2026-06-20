"""Tests for AppWsChannelAdapter downlink materialization."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.core.companion_harness.tools.tool_background import ToolOutputEvent
from app.schemas.chat import ChatCompletionRequest
from app.services.agentic_channel.adapters.app_ws import (
    AppWsChannelAdapter,
    AppWsTurnContext,
)
from app.services.agentic_channel.scope_queue_serving import (
    ScopeDrainCompletion,
)
from app.services.agentic_channel.channel_runtime import (
    ChannelRuntimeState,
    clear_registries_for_tests,
    get_scope_channel_registry,
)
from app.services.agentic_channel.presence import clear_presences_for_tests
from app.services.agentic_companion.downlink import Downlink, DownlinkKind
from app.services.agentic_companion.ws_turn_support import (
    companion_ai_meta_from_queue_delivery,
)


@pytest.fixture(autouse=True)
def _clear_channel_registries() -> None:
    clear_presences_for_tests()
    clear_registries_for_tests()


@pytest.mark.asyncio
async def test_app_ws_user_reply_downlink_sets_queue_message_id_meta() -> None:
    scope = AgentScope(user_id="user-app-ws", agent_id="agent-app-ws")
    outbound_queue: asyncio.Queue = asyncio.Queue()
    db = AsyncMock()
    request = ChatCompletionRequest(
        messages=[{"role": "user", "content": "hi"}]
    )
    queue_message_id = "queue-msg-uuid-1"
    expected_meta = companion_ai_meta_from_queue_delivery(
        queue_message_id=queue_message_id,
        tool_background_started=False,
    )
    turn_ctx = AppWsTurnContext(
        db=db,
        session_id="session-1",
        agent_id="agent-app-ws",
        chat_id="chat-row-42",
        request=request,
        last_user_message={"role": "user", "content": "hi"},
        last_user_text="hi",
        effective_local_id="local-1",
        client_message_id="client-uuid-1",
        queue_message_id=queue_message_id,
    )
    adapter = AppWsChannelAdapter(
        scope=scope,
        outbound_queue=outbound_queue,
        db=db,
        foreground_ctx_lookup=lambda _uid: None,
    )
    adapter.register_turn_context(turn_ctx, client_message_id="client-uuid-1")
    downlink = adapter.as_downlink()

    with (
        patch(
            "app.services.agentic_companion.ws_outbound_materialize.persist_companion_user_message_for_queue_delivery",
            new_callable=AsyncMock,
            return_value=101,
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
                "meta_data": expected_meta,
                "timestamp": "2025-01-01T00:00:00+00:00",
                "audio_url": None,
            },
        ),
        patch(
            "app.services.agentic_companion.ws_outbound_materialize.chat_history_service.get_latest_user_message_id",
            new_callable=AsyncMock,
            return_value=101,
        ),
        patch(
            "app.services.agentic_companion.ws_outbound_materialize.agent_status_line_for_chat_header",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        await downlink.deliver(
            Downlink(
                kind=DownlinkKind.USER_REPLY,
                assistant_text="hello queue",
                turn=None,
                tool_output=None,
                bootstrap_interim=None,
                scheduled_task_id=None,
                transcript_user_text=None,
                message_ids=(queue_message_id,),
            )
        )

    payload = await outbound_queue.get()
    assert payload["code"] == 200
    assert payload["agent_id"] == "agent-app-ws"
    assert payload["data"]["choices"][0]["message"]["content"] == "hello queue"
    assert (
        payload["data"]["choices"][0]["message"]["meta_data"]["user_msg_uuid"]
        == queue_message_id
    )


@pytest.mark.asyncio
async def test_app_ws_turn_context_dropped_on_drain_complete() -> None:
    scope = AgentScope(user_id="user-drain", agent_id="agent-drain")
    adapter = AppWsChannelAdapter(
        scope=scope,
        outbound_queue=asyncio.Queue(),
        db=AsyncMock(),
        foreground_ctx_lookup=lambda _uid: None,
    )
    turn_ctx = AppWsTurnContext(
        db=AsyncMock(),
        session_id="session-1",
        agent_id="agent-drain",
        chat_id="chat-1",
        request=ChatCompletionRequest(
            messages=[{"role": "user", "content": "hi"}]
        ),
        last_user_message={"role": "user", "content": "hi"},
        last_user_text="hi",
        effective_local_id=None,
        client_message_id="client-1",
        queue_message_id="queue-1",
    )
    adapter.register_turn_context(turn_ctx, client_message_id="client-1")
    adapter.on_queue_drain_complete(
        ScopeDrainCompletion(
            input_message_ids=("queue-1",),
            tool_background_started=False,
        )
    )
    assert adapter._lookup_turn_context(("queue-1",)) is None


@pytest.mark.asyncio
async def test_app_ws_tool_background_downlink_sets_langsmith_meta() -> None:
    scope = AgentScope(user_id="user-tb", agent_id="agent-tb")
    outbound_queue: asyncio.Queue = asyncio.Queue()
    db = AsyncMock()
    request = ChatCompletionRequest(
        messages=[{"role": "user", "content": "go"}]
    )
    foreground_pending: dict[str, dict] = {
        "user-msg-uuid": {
            "session_id": "session-tb",
            "agent_id": "agent-tb",
            "request": request,
            "effective_local_id": "local-tb",
            "foreground_user_message_id": 55,
        }
    }
    adapter = AppWsChannelAdapter(
        scope=scope,
        outbound_queue=outbound_queue,
        db=db,
        foreground_ctx_lookup=lambda uid: foreground_pending.get(uid),
    )
    downlink = adapter.as_downlink()
    memory_store = MagicMock()
    ev = ToolOutputEvent(
        scope_registry_key=scope.registry_key(),
        memory_store=memory_store,
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

    captured_meta: dict = {}

    async def _capture_ai_message(
        session_id, message, agent_id=None, meta_data=None, **_kwargs
    ):
        if meta_data is not None:
            captured_meta.update(meta_data)
        return 303

    import app.services.agentic_companion.ws_outbound_materialize as mat

    with (
        patch(
            "app.services.agentic_companion.ws_outbound_materialize.chat_history_service.add_ai_message_sync_async",
            side_effect=_capture_ai_message,
        ),
        patch(
            "app.services.agentic_companion.ws_outbound_materialize.chat_history_service.get_ai_message_info_by_id",
            new_callable=AsyncMock,
            return_value={
                "id": 303,
                "meta_data": captured_meta,
                "timestamp": "2025-01-01T00:00:00+00:00",
                "audio_url": None,
            },
        ),
        patch(
            "app.services.agentic_companion.ws_outbound_materialize.agent_status_line_for_chat_header",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch.object(
            mat, "generated_image_meta_from_index_slice", return_value=None
        ),
    ):
        await downlink.deliver(
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

    payload = await outbound_queue.get()
    assert payload["code"] == 200
    assert captured_meta["source"] == "tool_bg"
    assert captured_meta["langsmith_trace_id"] == "ls-trace"
    assert captured_meta["langsmith_run_id"] == "ls-run"
    assert captured_meta["reply_to_user_msg_uuid"] == "user-msg-uuid"


@pytest.mark.asyncio
async def test_app_ws_turn_context_chat_id_uses_real_chat_row_id() -> None:
    """Delivery ctx must bind chat_id to str(chat.id), not memory_store_chat_id."""
    chat = SimpleNamespace(id="legacy-chat-row-99")
    turn_ctx = AppWsTurnContext(
        db=AsyncMock(),
        session_id="session-boundary",
        agent_id="agent-boundary",
        chat_id=str(chat.id),
        request=ChatCompletionRequest(
            messages=[{"role": "user", "content": "x"}]
        ),
        last_user_message={"role": "user", "content": "x"},
        last_user_text="x",
        effective_local_id=None,
        client_message_id=None,
    )
    assert turn_ctx.chat_id == "legacy-chat-row-99"


@pytest.mark.asyncio
async def test_presence_deliver_ready_routes_user_reply_to_app_adapter() -> (
    None
):
    scope = AgentScope(user_id="user-pres-app", agent_id="agent-pres-app")
    outbound_queue: asyncio.Queue = asyncio.Queue()
    db = AsyncMock()
    adapter = AppWsChannelAdapter(
        scope=scope,
        outbound_queue=outbound_queue,
        db=db,
        foreground_ctx_lookup=lambda _uid: None,
    )
    registry = get_scope_channel_registry(scope)
    registry.states[CompanionRuntimeChannel.APP] = ChannelRuntimeState.ACTIVE
    registry.adapters[CompanionRuntimeChannel.APP] = adapter
    registry.downlinks[CompanionRuntimeChannel.APP] = adapter.as_downlink()

    from app.services.agentic_channel.presence import AgentChannelPresence
    from app.core.companion_harness.agentic_companion.output_queue import (
        ReadyOutputMessage,
    )

    presence = AgentChannelPresence(scope)
    queue_message_id = "queue-redelivery-1"
    turn_ctx = AppWsTurnContext(
        db=db,
        session_id="session-redelivery",
        agent_id="agent-pres-app",
        chat_id="chat-redelivery",
        request=ChatCompletionRequest(
            messages=[{"role": "user", "content": "hi"}]
        ),
        last_user_message={"role": "user", "content": "hi"},
        last_user_text="hi",
        effective_local_id=None,
        client_message_id=None,
        queue_message_id=queue_message_id,
    )
    adapter.register_turn_context(turn_ctx, client_message_id=None)

    with (
        patch(
            "app.services.agentic_companion.ws_outbound_materialize.persist_companion_user_message_for_queue_delivery",
            new_callable=AsyncMock,
            return_value=11,
        ),
        patch(
            "app.services.agentic_companion.ws_outbound_materialize.chat_history_service.add_ai_message_sync_async",
            new_callable=AsyncMock,
            return_value=22,
        ),
        patch(
            "app.services.agentic_companion.ws_outbound_materialize.chat_history_service.get_ai_message_info_by_id",
            new_callable=AsyncMock,
            return_value={
                "id": 22,
                "meta_data": {},
                "timestamp": "2025-01-01T00:00:00+00:00",
                "audio_url": None,
            },
        ),
        patch(
            "app.services.agentic_companion.ws_outbound_materialize.chat_history_service.get_latest_user_message_id",
            new_callable=AsyncMock,
            return_value=11,
        ),
        patch(
            "app.services.agentic_companion.ws_outbound_materialize.agent_status_line_for_chat_header",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        await presence._deliver_ready_via_active_channel(
            ReadyOutputMessage(
                message_id="out-redeliver",
                batch_id="batch-redeliver",
                kind=DownlinkKind.USER_REPLY,
                text="redelivered reply",
                sequence=1,
                message_ids=(queue_message_id,),
            )
        )

    payload = await outbound_queue.get()
    assert (
        payload["data"]["choices"][0]["message"]["content"]
        == "redelivered reply"
    )
