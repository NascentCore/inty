"""Turn routing for companion kernel: in-turn LLM strategy labels.

``*_SYNC`` members mean a **single in-turn** ``chat_completion`` path (no async foreground chat +
``tool_background`` split). They do **not** describe WebSocket blocking or whether the HTTP handler
awaits the full turn.

When tools are enabled, ``run_turn`` resolves the user-visible assistant string from the **foreground**
envelope chat before spawning ``tool_background``; the latter's tool-model rounds are not awaited for
that return value (monolog inner tick skips foreground—see ``turn`` module docstring / companion AGENTS).

TODO(#3398): Debate single-LLM in-turn sync vs dual-LLM (foreground chat + ``tool_background``) for user chat.
"""

from __future__ import annotations

from enum import Enum
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from .models import InnerTickActivity

if TYPE_CHECKING:
    from app.core.companion_harness.tools.tool_background import ToolOutputEvent

BackgroundToolEventSink = Callable[["ToolOutputEvent"], None]


# TODO(#3402): Replace with channel-agnostic ``UserVisibleChunk`` + ``UserVisibleChunkSink``.
class BootstrapInterimOutput(BaseModel):
    """One bootstrap sync tool-loop LLM round delivered to the client before turn end."""

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
    When ``tools_enabled``, routing is always ``ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL``
    (tools run only in ``tool_background``). Otherwise in-turn sync chat uses
    ``PROACTIVE_CHAT_SYNC``, ``INNER_TICK_SYNC``, or ``CHAT_ONLY_SYNC``.

    TODO(#3401): ``TurnRouteMode`` conflates ``CompanionTurnTrack`` with loop mechanism;
    introduce ``AgenticLoopMechanism`` and resolve via ``resolve_agentic_loop(track, config)``.
    """

    # TODO(#3401): rename members to drop ``_SYNC`` / avoid leaking execution-strategy names;
    # prefer track-aligned or product semantics (e.g. inner-tick mode labels).
    PROACTIVE_CHAT_SYNC = "proactive_chat_sync"
    INNER_TICK_SYNC = "inner_tick_sync"
    CHAT_ONLY_SYNC = "chat_only_sync"
    ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL = (
        "async_foreground_chat_background_tool"
    )


def resolve_turn_route_mode(
    *,
    inner_tick_turn: bool,
    inner_tick_activity: InnerTickActivity,
    tools_enabled: bool,
) -> TurnRouteMode:
    """Pick route label. Tools always use async foreground chat + background tool thread.

    TODO(#3398): ``llm_loop_mode`` may switch settled ``USER_CHAT`` to in-turn sync — child #3369.
    """
    if tools_enabled:
        return TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL
    if (
        inner_tick_turn
        and inner_tick_activity == InnerTickActivity.PROACTIVE_CHAT
    ):
        return TurnRouteMode.PROACTIVE_CHAT_SYNC
    if inner_tick_turn:
        return TurnRouteMode.INNER_TICK_SYNC
    return TurnRouteMode.CHAT_ONLY_SYNC
