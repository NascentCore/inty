"""App WebSocket channel adapter for stateless OutputQueue delivery."""

from __future__ import annotations

import asyncio

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.output_queue import (
    OutputDeliveryUnroutableError,
    ReadyOutputMessage,
)
from app.core.companion_harness.agentic_companion.postgres_queue import (
    PostgresInputQueueRepository,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.db.session import AsyncSessionLocal
from app.schemas.chat import ChatCompletionRequest, ChatMessage
from app.services.agentic_companion.downlink import (
    ChannelDownlink,
    Downlink,
    DownlinkKind,
    downlink_delivers_user_visible_text,
)
from app.services.agentic_companion.inner_tick_delivery import (
    InnerTickDelivery,
    inner_tick_delivery_for_ws,
)
from app.services.agentic_companion.ws_outbound_materialize import (
    materialize_queue_user_reply_from_durable,
    materialize_tool_background_ws_payload,
)
from app.services.chat_service import generate_session_id
from app.services.ws_session_messages import WsOutboundPayload


class AppWsChannelAdapter:
    """Materialize durable queue rows onto one App WebSocket outbound queue."""

    def __init__(
        self,
        *,
        scope: AgentScope,
        outbound_queue: asyncio.Queue[WsOutboundPayload],
    ) -> None:
        assert scope is not None
        assert outbound_queue is not None
        self._scope = scope
        self._outbound_queue = outbound_queue

    @property
    def channel(self) -> CompanionRuntimeChannel:
        return CompanionRuntimeChannel.APP

    def as_downlink(self) -> ChannelDownlink:
        return _AppWsChannelDownlink(adapter=self)

    def inner_tick_delivery(self) -> InnerTickDelivery:
        return inner_tick_delivery_for_ws(self._outbound_queue)

    async def on_turn_up(self, scope: AgentScope) -> None:
        assert scope is not None

    async def on_turn_down(self, scope: AgentScope) -> None:
        assert scope is not None


class _AppWsChannelDownlink:
    """Deliver USER_REPLY (from OutputQueue) and TOOL_BACKGROUND on App WS."""

    def __init__(self, *, adapter: AppWsChannelAdapter) -> None:
        self._adapter = adapter

    async def deliver(self, event: Downlink) -> None:
        if not downlink_delivers_user_visible_text(event):
            return
        match event.kind:
            case DownlinkKind.USER_REPLY:
                await self._deliver_user_reply(event)
            case DownlinkKind.TOOL_BACKGROUND:
                await self._deliver_tool_background(event)
            case _:
                return

    async def _deliver_user_reply(self, event: Downlink) -> None:
        message = event.output_message
        assert isinstance(message, ReadyOutputMessage)
        async with AsyncSessionLocal() as db:
            input_repo = PostgresInputQueueRepository(db)
            input_records = await input_repo.get_records_by_ids(
                self._adapter._scope,
                message.message_ids,
            )
            if len(input_records) != len(message.message_ids):
                raise OutputDeliveryUnroutableError(
                    self._adapter._scope,
                    message.message_ids,
                )
            payload = await materialize_queue_user_reply_from_durable(
                db=db,
                scope=self._adapter._scope,
                message=message,
                input_records=input_records,
            )
        await self._adapter._outbound_queue.put(payload)

    async def _deliver_tool_background(self, event: Downlink) -> None:
        tool_output = event.tool_output
        assert tool_output is not None
        async with AsyncSessionLocal() as db:
            input_repo = PostgresInputQueueRepository(db)
            input_records = await input_repo.get_records_by_ids(
                self._adapter._scope,
                (tool_output.user_msg_uuid,),
            )
            if not input_records:
                raise OutputDeliveryUnroutableError(
                    self._adapter._scope,
                    (tool_output.user_msg_uuid,),
                )
            input_record = input_records[-1]
            request = ChatCompletionRequest(
                messages=[
                    ChatMessage(role="user", content=input_record.text),
                ],
                message_id=input_record.message_id,
            )
            payload = await materialize_tool_background_ws_payload(
                db=db,
                agent_id=self._adapter._scope.agent_id,
                session_id=generate_session_id(
                    self._adapter._scope.memory_store_chat_id()
                ),
                ev=tool_output,
                request=request,
                effective_local_id=input_record.local_id,
                foreground_user_message_id=input_record.chat_history_user_row_id,
            )
        await self._adapter._outbound_queue.put(payload)
