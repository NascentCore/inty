"""Channel-agnostic downlink events from agentic companion session to a transport adapter.

agentic_companion 里的 presence 指：用户与 companion 处于同一段「在线会话」期间，进程内那套共享 runtime

WebSocket and Weixin adapters translate :class:`Downlink` into
``ChatWebSocketResponse`` / Hermes ``send_text`` without re-entering ``/api/v1/chat/ws``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from app.core.companion_harness.companion.models import CompanionTurnResult
from app.core.companion_harness.companion.turn_routes import BootstrapInterimOutput
from app.core.companion_harness.tools.tool_background import ToolOutputEvent


class DownlinkKind(StrEnum):
    """How the presence layer classified an assistant-facing delivery.

    One value per production downlink path in ``chat_ws``.
    """

    USER_REPLY = "user_reply"  # Foreground user-chat turn finished; implicit ``user_signed_on`` greeting when ``assistant_source == \"greeting\"``
    PROACTIVE = "proactive"  # Inner-tick proactive chat (synthetic user line + assistant reply)
    MAINTENANCE = "maintenance"  # Inner-tick maintenance; ``assistant_text`` may be empty (tool_bg-only)
    SCHEDULED = "scheduled"  # Due ``schedule_queue`` reminder inner-tick
    TOOL_BACKGROUND = "tool_background"  # Async ``tool_background`` loop produced user-visible text
    BOOTSTRAP_INTERIM = "bootstrap_interim"  # Bootstrap sync tool-loop LLM round before ``USER_CHAT_BOOTSTRAP`` ends


@dataclass(frozen=True)
class Downlink:
    """One assistant-facing delivery decision, independent of WebSocket vs Weixin encoding.

    Use the module factories (``user_reply_downlink``, …) so ``kind`` matches populated
    payload fields. ``assistant_text`` is what end users should see when the event is
    delivered; it may be empty for maintenance ``tool_bg_only`` turns (no WS/Weixin push).
    """

    kind: DownlinkKind
    assistant_text: str
    turn: CompanionTurnResult | None
    tool_output: ToolOutputEvent | None
    bootstrap_interim: BootstrapInterimOutput | None
    scheduled_task_id: str | None
    transcript_user_text: str | None


class ChannelDownlink(Protocol):
    """Transport adapter: materialize and send one :class:`Downlink`."""

    async def deliver(self, event: Downlink) -> None:
        """Deliver ``event`` on this channel (WS queue pump, Weixin peer text, etc.)."""


def user_reply_downlink(*, turn: CompanionTurnResult) -> Downlink:
    """Foreground user-chat (or implicit greeting) turn finished."""
    assert turn is not None
    return Downlink(
        kind=DownlinkKind.USER_REPLY,
        assistant_text=turn.assistant_text,
        turn=turn,
        tool_output=None,
        bootstrap_interim=None,
        scheduled_task_id=None,
        transcript_user_text=None,
    )


def proactive_downlink(
    *,
    turn: CompanionTurnResult,
    transcript_user_text: str,
) -> Downlink:
    """Inner-tick proactive chat: synthetic user line + assistant reply."""
    assert turn is not None
    assert transcript_user_text.strip()
    return Downlink(
        kind=DownlinkKind.PROACTIVE,
        assistant_text=turn.assistant_text,
        turn=turn,
        tool_output=None,
        bootstrap_interim=None,
        scheduled_task_id=None,
        transcript_user_text=transcript_user_text,
    )


def maintenance_downlink(
    *,
    turn: CompanionTurnResult,
    transcript_user_text: str,
) -> Downlink:
    """Inner-tick maintenance; ``assistant_text`` may be empty (tool_bg-only, no user push)."""
    assert turn is not None
    assert transcript_user_text.strip()
    return Downlink(
        kind=DownlinkKind.MAINTENANCE,
        assistant_text=turn.assistant_text,
        turn=turn,
        tool_output=None,
        bootstrap_interim=None,
        scheduled_task_id=None,
        transcript_user_text=transcript_user_text,
    )


def scheduled_downlink(
    *,
    turn: CompanionTurnResult,
    transcript_user_text: str,
    scheduled_task_id: str,
) -> Downlink:
    """Due ``schedule_queue`` reminder inner-tick."""
    assert turn is not None
    assert transcript_user_text.strip()
    assert scheduled_task_id.strip()
    return Downlink(
        kind=DownlinkKind.SCHEDULED,
        assistant_text=turn.assistant_text,
        turn=turn,
        tool_output=None,
        bootstrap_interim=None,
        scheduled_task_id=scheduled_task_id.strip(),
        transcript_user_text=transcript_user_text,
    )


def tool_background_downlink(*, tool_output: ToolOutputEvent) -> Downlink:
    """Async tool loop produced user-visible text (may be suppressed by adapter flags)."""
    assert tool_output is not None
    return Downlink(
        kind=DownlinkKind.TOOL_BACKGROUND,
        assistant_text=tool_output.text,
        turn=None,
        tool_output=tool_output,
        bootstrap_interim=None,
        scheduled_task_id=None,
        transcript_user_text=None,
    )


def bootstrap_interim_downlink(
    *,
    interim: BootstrapInterimOutput,
) -> Downlink:
    """One bootstrap sync tool-loop LLM round before ``USER_CHAT_BOOTSTRAP`` ends."""
    assert interim is not None
    return Downlink(
        kind=DownlinkKind.BOOTSTRAP_INTERIM,
        assistant_text=interim.text,
        turn=None,
        tool_output=None,
        bootstrap_interim=interim,
        scheduled_task_id=None,
        transcript_user_text=None,
    )


def downlink_delivers_user_visible_text(event: Downlink) -> bool:
    """Whether adapters should push assistant text to the human on this channel."""
    match event.kind:
        case DownlinkKind.TOOL_BACKGROUND:
            assert event.tool_output is not None
            return bool(event.tool_output.output_to_user) and bool(
                event.assistant_text.strip()
            )
        case DownlinkKind.MAINTENANCE:
            return bool(event.assistant_text.strip())
        case (
            DownlinkKind.USER_REPLY
            | DownlinkKind.PROACTIVE
            | DownlinkKind.SCHEDULED
            | DownlinkKind.BOOTSTRAP_INTERIM
        ):
            return bool(event.assistant_text.strip())
        case _:
            return False
