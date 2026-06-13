"""Route resolution for agent.companion_harness.user_turn.llm_loop_mode."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.core.companion_harness.companion.models import InnerTickActivity
from app.core.companion_harness.companion.turn_routes import (
    TurnRouteMode,
    resolve_turn_route_mode,
)
from app.utils.config import UserTurnLlmLoopMode


def _patch_llm_loop_mode(mode: UserTurnLlmLoopMode):
    agent = SimpleNamespace(
        companion_harness=SimpleNamespace(
            user_turn=SimpleNamespace(llm_loop_mode=mode)
        )
    )
    return patch(
        "app.core.companion_harness.companion.turn_routes.global_config_loaded_from_config_yaml",
        SimpleNamespace(agent=agent),
    )


def test_resolve_turn_route_mode_dual_llm_for_user_chat_tools() -> None:
    with _patch_llm_loop_mode(UserTurnLlmLoopMode.DUAL_LLM):
        route = resolve_turn_route_mode(
            inner_tick_turn=False,
            inner_tick_activity=InnerTickActivity.MAINTENANCE,
            tools_enabled=True,
        )
    assert route == TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL


def test_resolve_turn_route_mode_in_turn_single_llm_for_user_chat_tools() -> None:
    with _patch_llm_loop_mode(UserTurnLlmLoopMode.IN_TURN_SINGLE_LLM):
        route = resolve_turn_route_mode(
            inner_tick_turn=False,
            inner_tick_activity=InnerTickActivity.MAINTENANCE,
            tools_enabled=True,
        )
    assert route == TurnRouteMode.IN_TURN_SYNC_TOOL


def test_resolve_turn_route_mode_maintenance_stays_async_dual() -> None:
    with _patch_llm_loop_mode(UserTurnLlmLoopMode.IN_TURN_SINGLE_LLM):
        route = resolve_turn_route_mode(
            inner_tick_turn=True,
            inner_tick_activity=InnerTickActivity.MAINTENANCE,
            tools_enabled=True,
        )
    assert route == TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL


def test_resolve_turn_route_mode_no_tools_chat_only() -> None:
    with _patch_llm_loop_mode(UserTurnLlmLoopMode.IN_TURN_SINGLE_LLM):
        route = resolve_turn_route_mode(
            inner_tick_turn=False,
            inner_tick_activity=InnerTickActivity.MAINTENANCE,
            tools_enabled=False,
        )
    assert route == TurnRouteMode.CHAT_ONLY_SYNC
