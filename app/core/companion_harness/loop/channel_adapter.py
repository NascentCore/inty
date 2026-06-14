"""Loop channel adapter for per-call-streaming downlinks."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.agentic_companion.downlink import ChannelDownlink, Downlink


class LoopChannelAdapter:
    """Transport-agnostic sink for projected ``Downlink`` events."""

    async def deliver(self, event: Downlink) -> None:
        """Deliver one downlink (WS / Weixin / test recorder)."""
        raise NotImplementedError


@dataclass
class RecordingChannelAdapter(LoopChannelAdapter):
    """In-memory channel for tests and parity smoke."""

    events: list[Downlink] = field(default_factory=list)

    async def deliver(self, event: Downlink) -> None:
        self.events.append(event)


class DownlinkLoopChannelAdapter(LoopChannelAdapter):
    """Forward loop projected downlinks to one ``ChannelDownlink``."""

    def __init__(self, inner: ChannelDownlink) -> None:
        assert inner is not None
        self._inner = inner

    async def deliver(self, event: Downlink) -> None:
        await self._inner.deliver(event)
