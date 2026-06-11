"""Ops telegram-demo: Telegram Bot API ↔ companion harness (in-process, no ``/api/v1/chat/ws``).

TODO(telegram-demo-onboard-web): Like ``/weixin``, auto-select or create companion on
``GET /telegram-demo`` so testers need not paste ``agent_id``.
"""

from __future__ import annotations

import asyncio

from loguru import logger

from app.core.config import global_config_loaded_from_config_yaml
from app.external_services.telegram_bot_api import TelegramBotApi
from app.utils.config import resolved_telegram_bot_token

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
    _transport = TelegramTransport(api=api)
    _poll_task = asyncio.create_task(
        _transport.run_until_stopped(),
        name="telegram_demo_poll",
    )
    logger.info("telegram-demo: long-poll started")


async def stop_telegram_demo() -> None:
    """Stop long-poll task and release transport."""
    global _poll_task, _transport
    transport = _transport
    task = _poll_task
    _transport = None
    _poll_task = None
    if transport is not None:
        await transport.stop()
    if task is not None and (not task.done()):
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    logger.info("telegram-demo: stopped")
