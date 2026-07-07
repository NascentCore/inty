"""Channel-agnostic downlink events from agentic companion session to a transport adapter.

agentic_companion 里的 presence 指：用户与 companion 处于同一段「在线会话」期间，进程内那套共享 runtime

WebSocket and Weixin adapters translate :class:`Downlink` into
``ChatWebSocketResponse`` / Hermes ``send_text`` without re-entering ``/api/v1/chat/ws``.

TODO(retire-downlink-event): The ``Downlink`` dataclass, its ``*_downlink`` factories, and
  ``downlink_delivers_user_visible_text`` are superseded by ``ReadyOutputMessage`` /
  ``ready_output_delivers_user_visible_text``; adapters now consume durable OutputQueue rows
  via ``ChannelDownlink.deliver(message)``. They have no production caller. Delete them in
  #3398 P3 and rename ``DownlinkKind`` → ``OutputMessageKind`` (keep only ``DownlinkKind`` and
  the ``ChannelDownlink`` protocol until then).
TODO(channel-outbound-affordances): Extend the adapter port with reply threading and emoji
  reaction targets; map transcript UUIDs ↔ channel message IDs — #3440
TODO(!3451, !3452): Carry user-visible image assets explicitly for native channel image bubbles.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from app.core.companion_harness.agentic_companion.output_queue import (
        ReadyOutputMessage,
    )
from app.core.companion_harness.companion.models import CompanionTurnResult
from app.core.companion_harness.companion.turn_routes import (
    BootstrapInterimOutput,
)
from app.core.companion_harness.tools.tool_background import ToolOutputEvent


class DownlinkKind(StrEnum):
    """How the presence layer classified an assistant-facing delivery.

    One value per production downlink path in ``chat_ws``.
    """

    USER_REPLY = "user_reply"  # Foreground user-chat turn finished; implicit ``user_signed_on`` greeting when ``assistant_source == \"greeting\"``
    PROACTIVE = "proactive"  # Inner-tick proactive chat (synthetic user line + assistant reply)
    MONOLOG = "monolog"  # Inner-tick monolog; ``assistant_text`` may be empty (tool_bg-only)
    SCHEDULED = "scheduled"  # Due ``schedule_queue`` reminder inner-tick
    TOOL_BACKGROUND = "tool_background"  # Async ``tool_background`` loop produced user-visible text
    BOOTSTRAP_INTERIM = "bootstrap_interim"  # Bootstrap sync tool-loop LLM round before ``USER_CHAT_BOOTSTRAP`` ends
    # TODO(!3402): Add ``USER_VISIBLE_CHUNK`` for user-turn per-round delivery; retire ``BOOTSTRAP_INTERIM``.


@dataclass(frozen=True)
class Downlink:
    """One assistant-facing delivery decision, independent of WebSocket vs Weixin encoding.

    Use the module factories (``user_reply_downlink``, …) so ``kind`` matches populated
    payload fields. ``assistant_text`` is what end users should see when the event is
    delivered; it may be empty for monolog ``tool_bg_only`` turns (no WS/Weixin push).
    """

    kind: DownlinkKind
    assistant_text: str
    turn: CompanionTurnResult | None
    tool_output: ToolOutputEvent | None
    bootstrap_interim: BootstrapInterimOutput | None
    scheduled_task_id: str | None
    transcript_user_text: str | None
    message_ids: tuple[str, ...] = ()
    output_message: Any | None = None


class ChannelDownlink(Protocol):
    """Transport adapter: materialize and send one durable OutputQueue row."""

    async def deliver(self, message: "ReadyOutputMessage") -> None:
        """Deliver ``message`` on this channel (WS queue pump, Weixin peer text, etc.)."""


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
        message_ids=(),
        output_message=None,
    )


def agent_initiated_visible_downlink(
    *,
    kind: DownlinkKind,
    assistant_text: str,
    output_message: Any | None = None,
) -> Downlink:
    """OutputQueue agent-initiated visible line with no inbound correlation."""
    assert assistant_text.strip() != ""
    return Downlink(
        kind=kind,
        assistant_text=assistant_text,
        turn=None,
        tool_output=None,
        bootstrap_interim=None,
        scheduled_task_id=None,
        transcript_user_text=None,
        message_ids=(),
        output_message=output_message,
    )


def queue_user_reply_downlink(
    *,
    assistant_text: str,
    message_ids: tuple[str, ...],
    output_message: Any | None = None,
) -> Downlink:
    """OutputQueue-delivered user-chat reply correlated to inbound message ids."""
    assert assistant_text.strip() != ""
    assert message_ids
    return Downlink(
        kind=DownlinkKind.USER_REPLY,
        assistant_text=assistant_text,
        turn=None,
        tool_output=None,
        bootstrap_interim=None,
        scheduled_task_id=None,
        transcript_user_text=None,
        message_ids=message_ids,
        output_message=output_message,
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
        output_message=None,
    )


def monolog_downlink(
    *,
    turn: CompanionTurnResult,
    transcript_user_text: str,
) -> Downlink:
    """Inner-tick monolog; ``assistant_text`` may be empty (tool_bg-only, no user push)."""
    assert turn is not None
    assert transcript_user_text.strip()
    return Downlink(
        kind=DownlinkKind.MONOLOG,
        assistant_text=turn.assistant_text,
        turn=turn,
        tool_output=None,
        bootstrap_interim=None,
        scheduled_task_id=None,
        transcript_user_text=transcript_user_text,
        output_message=None,
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
        output_message=None,
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
        output_message=None,
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
        output_message=None,
    )


def downlink_delivers_user_visible_text(event: Downlink) -> bool:
    """Whether adapters should push assistant text to the human on this channel."""
    match event.kind:
        case DownlinkKind.TOOL_BACKGROUND:
            assert event.tool_output is not None
            return bool(event.tool_output.output_to_user) and bool(
                event.assistant_text.strip()
            )
        case DownlinkKind.MONOLOG:
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
