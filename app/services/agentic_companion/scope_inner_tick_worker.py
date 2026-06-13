"""Process-level scope inner-tick worker loop (#3255)."""

from __future__ import annotations

import asyncio

from loguru import logger

from app.core.config import global_config_loaded_from_config_yaml
from app.services.agentic_companion.scope_inner_tick_poll import (
    run_scope_inner_tick_poll_cycle,
)


async def run_scope_inner_tick_worker_loop(
    *,
    stop: asyncio.Event,
) -> None:
    """Poll all companion scopes on a fixed interval until ``stop`` is set."""
    poll_seconds = float(
        global_config_loaded_from_config_yaml.app.features.companion_ws_proactive_chat_poll_seconds
    )
    logger.info(
        "scope_inner_tick_worker started poll_seconds={}",
        poll_seconds,
    )
    while not stop.is_set():
        try:
            await run_scope_inner_tick_poll_cycle()
        except Exception as exc:
            logger.exception("scope_inner_tick_worker cycle failed: {}", exc)
        try:
            await asyncio.wait_for(stop.wait(), timeout=poll_seconds)
        except asyncio.TimeoutError:
            pass
    logger.info("scope_inner_tick_worker stopped")
