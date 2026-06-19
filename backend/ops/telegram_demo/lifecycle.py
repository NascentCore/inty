"""Ops telegram-demo process lifecycle: long-poll start/stop on Ops boot/shutdown.

TODO(telegram-launch-idle-shutdown): Periodic sweeper: last real user message > 24h →
  ``deactivate_companion_bond_and_runtime`` — #3534 (epic #3531).
"""

from __future__ import annotations

import asyncio

from loguru import logger

from app.core.config import global_config_loaded_from_config_yaml
from app.external_services.telegram_bot_api import TelegramBotApi
from app.services.agentic_channel.presence import stop_all_presences
from app.utils.config import resolved_telegram_bot_token
from backend.ops.telegram_demo.session_store import restore_persisted_bindings
from backend.ops.telegram_demo.transport import TelegramTransport

_poll_task: asyncio.Task[None] | None = None
_transport: TelegramTransport | None = None


async def start_telegram_demo() -> None:
    """Start shared-bot long-poll when ``agent.channels.telegram.bot_token`` is set."""
    global _poll_task, _transport
    token = resolved_telegram_bot_token(
        global_config_loaded_from_config_yaml.agent
    )
    if not token:
        logger.info("telegram-demo: no bot token configured; poll skipped")
        return
    if _poll_task is not None and (not _poll_task.done()):
        logger.warning("telegram-demo: poll already running")
        return

    api = TelegramBotApi(bot_token=token)
    await restore_persisted_bindings(api=api)
    _transport = TelegramTransport(api=api)
    _poll_task = asyncio.create_task(
        _transport.run_until_stopped(),
        name="telegram_demo_poll",
    )
    logger.info("telegram-demo: long-poll started")


async def stop_telegram_demo() -> None:
    """Stop long-poll task, all presences, and release transport."""
    global _poll_task, _transport
    transport = _transport
    task = _poll_task
    _transport = None
    _poll_task = None
    await stop_all_presences()
    if transport is not None:
        await transport.stop()
    if task is not None and (not task.done()):
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    logger.info("telegram-demo: stopped")
