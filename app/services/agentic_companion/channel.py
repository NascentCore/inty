"""ToChannel abstraction: one external conversation surface for agentic core."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.services.agentic_companion.downlink import ChannelDownlink, Downlink


class Channel(ABC):
    """One external conversation surface from agentic core's view (ToChannel)."""

    @abstractmethod
    async def deliver(self, message: Downlink) -> None:
        """Send one user-visible (or wire-specific) outbound event."""


@dataclass
class RecordingChannel(Channel):
    """In-memory channel for tests."""

    events: list[Downlink] = field(default_factory=list)

    async def deliver(self, message: Downlink) -> None:
        self.events.append(message)


class DownlinkChannel(Channel):
    """Adapt legacy ``ChannelDownlink`` to ``Channel``."""

    def __init__(self, inner: ChannelDownlink) -> None:
        assert inner is not None
        self._inner = inner

    async def deliver(self, message: Downlink) -> None:
        await self._inner.deliver(message)
