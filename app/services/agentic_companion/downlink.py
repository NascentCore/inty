"""Transport seam: deliver one durable OutputQueue row on the active channel."""

from __future__ import annotations

from typing import Protocol

from app.core.companion_harness.agentic_companion.output_queue import (
    ReadyOutputMessage,
)


class ChannelDownlink(Protocol):
    """Materialize and send one ReadyOutputMessage on this channel."""

    async def deliver(self, message: ReadyOutputMessage) -> None:
        """Deliver ``message`` on this channel (WS queue pump, Weixin peer text, etc.)."""
