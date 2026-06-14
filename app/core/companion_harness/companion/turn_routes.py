"""Turn routing for companion kernel: in-turn LLM strategy labels.

``*_SYNC`` members mean a **single in-turn** ``chat_completion`` path (no async foreground chat +
``tool_background`` split). They do **not** describe WebSocket blocking or whether the HTTP handler
awaits the full turn.

Settled ``USER_CHAT`` with tools uses ``IN_TURN_SYNC_TOOL`` (single chat model, in-turn tool loop).
``ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL`` remains for maintenance/autonomy inner ticks (``tool_background``
only). Epic debate on restoring dual-LLM for user chat: #3398.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Awaitable, Callable

from pydantic import BaseModel, ConfigDict

from .models import InnerTickActivity

if TYPE_CHECKING:
    from app.core.companion_harness.tools.tool_background import ToolOutputEvent

BackgroundToolEventSink = Callable[["ToolOutputEvent"], None]


class BootstrapInterimOutput(BaseModel):
    """One in-turn sync tool-loop LLM round delivered to the client before turn end."""

    model_config = ConfigDict(extra="forbid")

    text: str
    user_msg_uuid: str
    trace_id: str
    langsmith_trace_id: str
    langsmith_run_id: str
    round_index: int
    had_tool_calls: bool
    assistant_msg_uuid: str


BootstrapInterimOutputSink = Callable[[BootstrapInterimOutput], Awaitable[None]]


class TurnRouteMode(str, Enum):
    """Which in-turn LLM execution strategy ``run_turn`` uses for this round.

    ``*_SYNC``: one ``chat_completion`` in the turn thread (not WS sync/async semantics).
    Settled ``USER_CHAT`` with tools uses ``IN_TURN_SYNC_TOOL``. Maintenance and autonomy inner
    ticks use ``ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL`` (``tool_background`` only).
    """

    # TODO: rename members to drop ``_SYNC`` / avoid leaking execution-strategy names;
    # prefer track-aligned or product semantics (e.g. inner-tick mode labels).
    PROACTIVE_CHAT_SYNC = "proactive_chat_sync"
    INNER_TICK_SYNC = "inner_tick_sync"
    CHAT_ONLY_SYNC = "chat_only_sync"
    IN_TURN_SYNC_TOOL = "in_turn_sync_tool"
    ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL = (
        "async_foreground_chat_background_tool"
    )


def resolve_turn_route_mode(
    *,
    inner_tick_turn: bool,
    inner_tick_activity: InnerTickActivity,
    tools_enabled: bool,
) -> TurnRouteMode:
    """Pick route label from turn shape (no config.yaml reads).

    TODO(user-turn-llm-loop-mode): Optional ``llm_loop_mode`` config may restore
    ``ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL`` for settled ``USER_CHAT`` — epic #3398, child #3369.
    """
    if tools_enabled:
        if inner_tick_turn:
            return TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL
        return TurnRouteMode.IN_TURN_SYNC_TOOL
    if (
        inner_tick_turn
        and inner_tick_activity == InnerTickActivity.PROACTIVE_CHAT
    ):
        return TurnRouteMode.PROACTIVE_CHAT_SYNC
    if inner_tick_turn:
        return TurnRouteMode.INNER_TICK_SYNC
    return TurnRouteMode.CHAT_ONLY_SYNC
