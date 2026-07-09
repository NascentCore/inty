"""App WebSocket channel adapter for stateless OutputQueue delivery."""

from __future__ import annotations

import asyncio

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.agentic_companion.output_queue import (
    OutputDeliveryUnroutableError,
    ReadyOutputMessage,
    ready_output_delivers_user_visible_text,
    ready_output_is_agent_initiated_visible,
)
from app.core.agentic_companion.postgres_queue import (
    PostgresInputQueueRepository,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)
from app.db.session import AsyncSessionLocal
from app.core.agentic_companion.types import OutputMessageKind
from app.services.agentic_companion.downlink import ChannelDownlink
from app.services.agentic_companion.ws_outbound_materialize import (
    materialize_agent_initiated_ws_payload,
    materialize_queue_user_reply_from_durable,
    materialize_tool_background_from_durable,
)
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
    def channel(self) -> ChannelKind:
        return ChannelKind.APP_WS

    def as_downlink(self) -> ChannelDownlink:
        return _AppWsChannelDownlink(adapter=self)

    async def on_turn_up(self, scope: AgentScope) -> None:
        assert scope is not None

    async def on_turn_down(self, scope: AgentScope) -> None:
        assert scope is not None


class _AppWsChannelDownlink:
    """Deliver OutputQueue rows on App WS."""

    def __init__(self, *, adapter: AppWsChannelAdapter) -> None:
        self._adapter = adapter

    async def deliver(self, message: ReadyOutputMessage) -> None:
        if not ready_output_delivers_user_visible_text(message):
            return
        match message.kind:
            case OutputMessageKind.USER_REPLY:
                if ready_output_is_agent_initiated_visible(message):
                    await self._deliver_agent_initiated(message)
                else:
                    await self._deliver_user_reply(message)
            case (
                OutputMessageKind.PROACTIVE
                | OutputMessageKind.SCHEDULED
                | OutputMessageKind.MONOLOG
            ):
                await self._deliver_agent_initiated(message)
            case OutputMessageKind.TOOL_BACKGROUND:
                await self._deliver_tool_background(message)
            case _:
                return

    async def _deliver_agent_initiated(
        self, message: ReadyOutputMessage
    ) -> None:
        async with AsyncSessionLocal() as db:
            payload = await materialize_agent_initiated_ws_payload(
                db=db,
                scope=self._adapter._scope,
                message=message,
            )
        await self._adapter._outbound_queue.put(payload)

    async def _deliver_user_reply(self, message: ReadyOutputMessage) -> None:
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

    async def _deliver_tool_background(
        self, message: ReadyOutputMessage
    ) -> None:
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
            payload = await materialize_tool_background_from_durable(
                db=db,
                scope=self._adapter._scope,
                message=message,
                input_records=input_records,
            )
        await self._adapter._outbound_queue.put(payload)
