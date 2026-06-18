"""Per-call-streaming deliverables and output queue.

TODO(!3460): Retire this sidecar queue in favor of
agentic_companion/output_queue.py as the only user-visible OutputQueue.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol

from app.core.companion_harness.companion.turn_routes import (
    BootstrapInterimOutput,
)
from app.core.companion_harness.tools.tool_background import ToolOutputEvent

if TYPE_CHECKING:
    from .channel_adapter import LoopChannelAdapter


class LoopDeliverableKind(StrEnum):
    """Wide loop emission kinds mapped to ``DownlinkKind`` via projection."""

    BOOTSTRAP_INTERIM = "bootstrap_interim"
    FOREGROUND_TEXT = "foreground_text"
    TOOL_BACKGROUND = "tool_background"
    USER_REPLY = "user_reply"


@dataclass(frozen=True)
class LoopDeliverable:
    """One user-visible or auditable delivery from an agentic loop."""

    kind: LoopDeliverableKind
    assistant_text: str
    bootstrap_interim: BootstrapInterimOutput | None
    tool_output: ToolOutputEvent | None
    significance_meta: dict[str, Any] | None
    turn_recall: str | None


class AgenticLoopOutputSink(Protocol):
    """Per-call-streaming sink for agentic loop mechanisms (channel or durable queue)."""

    @property
    def deliverables(self) -> tuple[LoopDeliverable, ...]:
        """Audit mirror of everything pushed."""

    async def push_bootstrap_interim(
        self, interim: BootstrapInterimOutput
    ) -> None:
        """Push one interim assistant round."""

    async def push_user_reply(self, *, assistant_text: str) -> None:
        """Push user-visible assistant text."""


class AgenticLoopOutputQueue(AgenticLoopOutputSink):
    """Per-call-streaming queue: each push immediately projects and delivers on channel.

    TODO(!3460): Legacy parity tests only; production should use the single
    agentic_companion OutputQueue through direct AgenticLoop user-turn methods.
    """

    def __init__(self, channel: LoopChannelAdapter) -> None:
        self._channel = channel
        self._mirror: list[LoopDeliverable] = []

    @property
    def deliverables(self) -> tuple[LoopDeliverable, ...]:
        """Audit mirror of everything pushed (not the primary UX path)."""
        return tuple(self._mirror)

    async def push_bootstrap_interim(
        self, interim: BootstrapInterimOutput
    ) -> None:
        """Push one bootstrap-style interim round (1-LLM tool round)."""
        deliverable = LoopDeliverable(
            kind=LoopDeliverableKind.BOOTSTRAP_INTERIM,
            assistant_text=interim.text,
            bootstrap_interim=interim,
            tool_output=None,
            significance_meta=None,
            turn_recall=None,
        )
        await self._push(deliverable)

    async def push_foreground_text(
        self,
        *,
        assistant_text: str,
        significance_meta: dict[str, Any] | None,
        turn_recall: str | None,
    ) -> None:
        """Push dual-LLM foreground envelope visible text (one LLM call)."""
        assert assistant_text.strip()
        deliverable = LoopDeliverable(
            kind=LoopDeliverableKind.FOREGROUND_TEXT,
            assistant_text=assistant_text,
            bootstrap_interim=None,
            tool_output=None,
            significance_meta=significance_meta,
            turn_recall=turn_recall,
        )
        await self._push(deliverable)

    async def push_tool_background(self, event: ToolOutputEvent) -> None:
        """Push one tool_background user-visible event."""
        deliverable = LoopDeliverable(
            kind=LoopDeliverableKind.TOOL_BACKGROUND,
            assistant_text=event.text,
            bootstrap_interim=None,
            tool_output=event,
            significance_meta=event.significance_perception,
            turn_recall=event.turn_recall,
        )
        await self._push(deliverable)

    async def push_user_reply(self, *, assistant_text: str) -> None:
        """Push terminal user-visible assistant text for this turn."""
        assert assistant_text.strip()
        deliverable = LoopDeliverable(
            kind=LoopDeliverableKind.USER_REPLY,
            assistant_text=assistant_text,
            bootstrap_interim=None,
            tool_output=None,
            significance_meta=None,
            turn_recall=None,
        )
        await self._push(deliverable)

    async def _push(self, deliverable: LoopDeliverable) -> None:
        from .projection import project_deliverable

        self._mirror.append(deliverable)
        downlink = project_deliverable(deliverable)
        await self._channel.deliver(downlink)
