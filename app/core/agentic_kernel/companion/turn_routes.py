"""Turn routing for companion kernel: chat vs tool_call vs inner_tick."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Callable

from .models import InnerTickMode

if TYPE_CHECKING:
    from .tool_background import ToolOutputEvent

BackgroundToolEventSink = Callable[["ToolOutputEvent"], None]


class TurnRouteMode(str, Enum):
    """Which execution strategy run_turn uses for this round.

    When ``tools_enabled``, routing is always ``ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL``
    (tools run only in ``tool_background``). Otherwise synchronous chat completion
    uses ``HEARTBEAT_SYNC``, ``INNER_TICK_SYNC``, or ``CHAT_ONLY_SYNC``.
    """

    HEARTBEAT_SYNC = "heartbeat_sync"
    INNER_TICK_SYNC = "inner_tick_sync"
    CHAT_ONLY_SYNC = "chat_only_sync"
    ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL = "async_foreground_chat_background_tool"


def resolve_turn_route_mode(
    *,
    inner_tick_turn: bool,
    inner_tick_mode: InnerTickMode,
    tools_enabled: bool,
) -> TurnRouteMode:
    """Pick route label. Tools always use async foreground chat + background tool thread."""
    if tools_enabled:
        return TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL
    if inner_tick_turn and inner_tick_mode == InnerTickMode.PROACTIVE_CHAT:
        return TurnRouteMode.HEARTBEAT_SYNC
    if inner_tick_turn:
        return TurnRouteMode.INNER_TICK_SYNC
    return TurnRouteMode.CHAT_ONLY_SYNC
