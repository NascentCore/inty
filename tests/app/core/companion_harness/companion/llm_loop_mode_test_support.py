"""Shared patches for ``agent.companion_harness.user_turn.llm_loop_mode`` tests."""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from typing import Iterator
from unittest.mock import patch

from app.utils.config import UserTurnLlmLoopMode

_TURN_ROUTES_GLOBAL_CONFIG = (
    "app.core.companion_harness.companion.turn_routes"
    ".global_config_loaded_from_config_yaml"
)


@contextmanager
def patch_user_turn_llm_loop_mode(
    mode: UserTurnLlmLoopMode,
) -> Iterator[None]:
    """Pin ``llm_loop_mode`` for ``resolve_turn_route_mode`` during a test."""
    agent = SimpleNamespace(
        companion_harness=SimpleNamespace(
            user_turn=SimpleNamespace(llm_loop_mode=mode)
        )
    )
    with patch(_TURN_ROUTES_GLOBAL_CONFIG, SimpleNamespace(agent=agent)):
        yield
