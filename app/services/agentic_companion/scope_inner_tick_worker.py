"""Process-level scope inner-tick worker loop (#3255)."""

from __future__ import annotations

import asyncio

from loguru import logger

from app.core.config import global_config_loaded_from_config_yaml
from app.services.agentic_companion.scope_inner_tick_poll import (
    run_scope_inner_tick_poll_cycle,
)


def scope_inner_tick_poll_interval_seconds() -> float:
    """Wake interval: min(presence poll, dreaming idle) so due checks are not starved."""
    feats = global_config_loaded_from_config_yaml.app.features
    presence_poll = float(feats.companion_ws_proactive_chat_poll_seconds)
    dreaming_idle = float(
        global_config_loaded_from_config_yaml.agent.companion_harness.dreaming_idle_seconds
    )
    return min(presence_poll, dreaming_idle)


async def run_scope_inner_tick_worker_loop(
    *,
    stop: asyncio.Event,
) -> None:
    """Poll all companion scopes on a fixed interval until ``stop`` is set."""
    poll_seconds = scope_inner_tick_poll_interval_seconds()
    logger.info(
        "scope_inner_tick_worker started poll_seconds={}",
        poll_seconds,
    )
    while not stop.is_set():
        try:
            await run_scope_inner_tick_poll_cycle(stop=stop)
        except Exception as exc:
            logger.exception("scope_inner_tick_worker cycle failed: {}", exc)
        if stop.is_set():
            break
        try:
            await asyncio.wait_for(stop.wait(), timeout=poll_seconds)
        except asyncio.TimeoutError:
            pass
    logger.info("scope_inner_tick_worker stopped")
