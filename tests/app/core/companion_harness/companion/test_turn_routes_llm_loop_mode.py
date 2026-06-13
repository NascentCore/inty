"""Route resolution for settled USER_CHAT in-turn sync vs inner-tick async."""

from __future__ import annotations

from app.core.companion_harness.companion.models import InnerTickActivity
from app.core.companion_harness.companion.turn_routes import (
    TurnRouteMode,
    resolve_turn_route_mode,
)


def test_resolve_turn_route_mode_user_chat_tools_uses_in_turn_sync() -> None:
    route = resolve_turn_route_mode(
        inner_tick_turn=False,
        inner_tick_activity=InnerTickActivity.MAINTENANCE,
        tools_enabled=True,
    )
    assert route == TurnRouteMode.IN_TURN_SYNC_TOOL


def test_resolve_turn_route_mode_maintenance_stays_async_dual() -> None:
    route = resolve_turn_route_mode(
        inner_tick_turn=True,
        inner_tick_activity=InnerTickActivity.MAINTENANCE,
        tools_enabled=True,
    )
    assert route == TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL


def test_resolve_turn_route_mode_no_tools_chat_only() -> None:
    route = resolve_turn_route_mode(
        inner_tick_turn=False,
        inner_tick_activity=InnerTickActivity.MAINTENANCE,
        tools_enabled=False,
    )
    assert route == TurnRouteMode.CHAT_ONLY_SYNC
