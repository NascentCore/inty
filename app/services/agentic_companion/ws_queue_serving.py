"""APP WebSocket helpers for the agentic companion serving pipeline."""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.types import (
    InboundWireMessage,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.services.agentic_channel.serving import (
    drain_scope_once_via_companion,
    enqueue_inbound_wire_message,
)


async def run_app_ws_user_turn_via_queues(
    *,
    scope: AgentScope,
    wire_id: str,
    user_text: str,
    implicit_signal_bundle: ImplicitSignalBundle,
    background_output_sink,
) -> str:
    """Enqueue one WS user message and drain one companion batch."""
    assert wire_id != ""
    assert user_text.strip() != ""
    inbound = InboundWireMessage(
        scope=scope,
        channel=CompanionRuntimeChannel.APP,
        wire_id=wire_id,
        text=user_text.strip(),
        received_at_utc=datetime.now(timezone.utc),
        client_message_id=None,
    )
    await enqueue_inbound_wire_message(inbound)
    return await drain_scope_once_via_companion(
        scope,
        runtime_channel=CompanionRuntimeChannel.APP,
        implicit_signal_bundle=implicit_signal_bundle,
        background_output_sink=background_output_sink,
    )
