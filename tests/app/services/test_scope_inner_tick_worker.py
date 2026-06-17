"""Tests for scope inner-tick worker poll interval."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.services.agentic_companion.scope_inner_tick_worker import (
    scope_inner_tick_poll_interval_seconds,
)


def test_scope_inner_tick_poll_interval_uses_min_of_presence_and_dreaming() -> None:
    cfg = MagicMock()
    cfg.app.features.companion_ws_proactive_chat_poll_seconds = 60.0
    cfg.agent.companion_harness.dreaming_idle_seconds = 300
    import app.services.agentic_companion.scope_inner_tick_worker as worker_mod

    original = worker_mod.global_config_loaded_from_config_yaml
    worker_mod.global_config_loaded_from_config_yaml = cfg
    try:
        assert scope_inner_tick_poll_interval_seconds() == 60.0
        cfg.agent.companion_harness.dreaming_idle_seconds = 30
        assert scope_inner_tick_poll_interval_seconds() == 30.0
    finally:
        worker_mod.global_config_loaded_from_config_yaml = original
