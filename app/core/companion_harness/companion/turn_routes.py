"""Turn routing for companion kernel: in-turn LLM strategy labels.

``*_SYNC`` members mean a **single in-turn** ``chat_completion`` path (no async foreground chat +
``tool_background`` split). They do **not** describe WebSocket blocking or whether the HTTP handler
awaits the full turn.

When tools are enabled, ``run_turn`` resolves the user-visible assistant string from the **foreground**
envelope chat before spawning ``tool_background``; the latter's tool-model rounds are not awaited for
that return value (maintenance inner tick skips foreground—see ``turn`` module docstring / companion AGENTS).
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Awaitable, Callable

from pydantic import BaseModel, ConfigDict

from app.core.config import global_config_loaded_from_config_yaml
from app.utils.config import UserTurnLlmLoopMode

from .models import InnerTickActivity

if TYPE_CHECKING:
    from app.core.companion_harness.tools.tool_background import ToolOutputEvent

BackgroundToolEventSink = Callable[["ToolOutputEvent"], None]


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
    When ``tools_enabled``, default routing is ``ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL``
    (tools run in ``tool_background``). Settled ``USER_CHAT`` may use ``IN_TURN_SYNC_TOOL``
    when ``agent.companion_harness.user_turn.llm_loop_mode`` is ``in_turn_single_llm``.
    Otherwise in-turn sync chat uses ``PROACTIVE_CHAT_SYNC``, ``INNER_TICK_SYNC``, or
    ``CHAT_ONLY_SYNC``.
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
    """Pick route label. Tools default to async foreground chat + background tool thread."""
    if tools_enabled:
        mode = (
            global_config_loaded_from_config_yaml.agent.companion_harness.user_turn.llm_loop_mode
        )
        if (
            not inner_tick_turn
            and mode == UserTurnLlmLoopMode.IN_TURN_SINGLE_LLM
        ):
            return TurnRouteMode.IN_TURN_SYNC_TOOL
        return TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL
    if (
        inner_tick_turn
        and inner_tick_activity == InnerTickActivity.PROACTIVE_CHAT
    ):
        return TurnRouteMode.PROACTIVE_CHAT_SYNC
    if inner_tick_turn:
        return TurnRouteMode.INNER_TICK_SYNC
    return TurnRouteMode.CHAT_ONLY_SYNC
