"""APP WebSocket helpers for the agentic companion serving pipeline.

TODO(!3487): Enqueue + wake only; remove ``drain_and_deliver_user_chat_turn`` await.
TODO(!3488): ``AppWsChannelAdapter`` on ``turn_channel_up``; one ``Coordinator`` per scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.types import (
    InboundWireMessage,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.core.companion_harness.companion.turn_routes import (
    BackgroundToolEventSink,
)
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.services.agentic_channel.serving import (
    SendTextFn,
    UserChatTurnDeliveryResult,
    drain_and_deliver_user_chat_turn,
    enqueue_inbound_wire_message,
)
from app.services.agentic_channel.turn import ensure_memory_store_session
from app.services.agentic_companion.ws_turn_support import (
    image_asset_baseline_for_scope_store,
)

if TYPE_CHECKING:
    from app.core.companion_harness.memory.memory_store import MemoryStore


@dataclass
class AppWsQueueDeliveryFlags:
    """Mutable delivery state shared between enqueue, drain, and send_text."""

    queue_message_id: str = ""
    tool_background_started: bool = False
    image_asset_baseline: int = 0
    image_asset_baseline_initialized: bool = False
    memory_store: MemoryStore | None = None


@dataclass(frozen=True)
class AppWsUserTurnQueueInput:
    """One App WS user-chat turn routed through durable InputQueue/OutputQueue."""

    scope: AgentScope
    wire_id: str
    user_text: str
    client_message_id: str | None
    implicit_signal_bundle: ImplicitSignalBundle
    background_output_sink: BackgroundToolEventSink | None
    delivery_flags: AppWsQueueDeliveryFlags
    send_text: SendTextFn


async def run_app_ws_user_turn_via_queues(
    queue_input: AppWsUserTurnQueueInput,
) -> UserChatTurnDeliveryResult:
    """Enqueue one WS user message, drain one batch, pull OutputQueue for delivery."""
    assert queue_input.wire_id != ""
    assert queue_input.user_text.strip() != ""
    inbound = InboundWireMessage(
        scope=queue_input.scope,
        channel=CompanionRuntimeChannel.APP,
        wire_id=queue_input.wire_id,
        text=queue_input.user_text.strip(),
        received_at_utc=datetime.now(timezone.utc),
        client_message_id=queue_input.client_message_id,
    )
    queue_message_id = await enqueue_inbound_wire_message(inbound)
    queue_input.delivery_flags.queue_message_id = queue_message_id
    session = await ensure_memory_store_session(queue_input.scope)
    queue_input.delivery_flags.image_asset_baseline = (
        image_asset_baseline_for_scope_store(session.store)
    )
    queue_input.delivery_flags.image_asset_baseline_initialized = True
    queue_input.delivery_flags.memory_store = session.store
    result = await drain_and_deliver_user_chat_turn(
        queue_input.scope,
        runtime_channel=CompanionRuntimeChannel.APP,
        delivery_wire_id=queue_input.wire_id,
        implicit_signal_bundle=queue_input.implicit_signal_bundle,
        background_output_sink=queue_input.background_output_sink,
        send_text=queue_input.send_text,
    )
    queue_input.delivery_flags.tool_background_started = (
        result.tool_background_started
    )
    return result
