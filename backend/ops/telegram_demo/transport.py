"""Telegram Bot API long-poll transport for Ops telegram-demo.

TODO(telegram-demo-text-only): Non-text inbound (photo, voice, sticker) is ignored.
"""

from __future__ import annotations

import asyncio

from loguru import logger

from app.external_services.telegram_bot_api import (
    TelegramBotApi,
    TelegramIncomingMessage,
)
from backend.ops.telegram_demo.binding import TelegramDemoBinding, parse_start_agent_id
from app.services.agentic_companion.runtime_channel_registry import (
    ActiveRuntimeChannel,
    other_active_channel,
    register_active_channel,
)
from backend.ops.telegram_demo.provision import provision_inty_for_telegram_chat
from backend.ops.telegram_demo.session_store import (
    get_binding,
    get_or_create_presence,
    put_binding,
)


class TelegramTransport:
    """Shared-bot getUpdates loop; routes text to in-process companion presence."""

    def __init__(self, *, api: TelegramBotApi) -> None:
        assert api is not None
        self._api = api
        self._offset: int | None = None
        self._stop = asyncio.Event()
        self._long_poll_timeout_seconds = 30

    async def run_until_stopped(self) -> None:
        while not self._stop.is_set():
            try:
                messages, next_offset = await asyncio.to_thread(
                    self._api.get_text_messages,
                    offset=self._offset,
                    timeout_seconds=self._long_poll_timeout_seconds,
                )
                if next_offset is not None:
                    self._offset = next_offset
                for inbound in messages:
                    reply = await self._handle_inbound(inbound)
                    if reply:
                        await asyncio.to_thread(
                            self._api.send_message,
                            chat_id=inbound.chat_id,
                            text=reply,
                        )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("telegram-demo poll iteration failed")
                await asyncio.sleep(2.0)

    async def stop(self) -> None:
        self._stop.set()

    async def _handle_inbound(self, inbound: TelegramIncomingMessage) -> str:
        agent_id = parse_start_agent_id(inbound.text)
        if agent_id is not None:
            return await self._handle_start(
                telegram_chat_id=inbound.chat_id,
                agent_id=agent_id,
            )
        binding = get_binding(inbound.chat_id)
        if binding is None:
            return (
                "请先通过 Ops /telegram-demo 页面获取链接，"
                "或在对话中发送 /start agent_{你的agent_id} 完成绑定。"
            )
        presence = get_or_create_presence(binding)
        return await presence.handle_user_text(inbound.text)

    async def _handle_start(
        self,
        *,
        telegram_chat_id: str,
        agent_id: str,
    ) -> str:
        try:
            provision = await provision_inty_for_telegram_chat(
                telegram_chat_id=telegram_chat_id,
                agent_id=agent_id,
            )
        except ValueError as exc:
            return str(exc)

        conflict = other_active_channel(
            user_id=provision.user_id,
            desired=ActiveRuntimeChannel.TELEGRAM,
        )
        if conflict is not None:
            return (
                f"该 Inty 用户已在 {conflict.value} 渠道活跃，"
                "请先关闭其他渠道后再绑定 Telegram。"
            )

        binding = TelegramDemoBinding(
            telegram_chat_id=telegram_chat_id,
            user_id=provision.user_id,
            agent_id=provision.agent_id,
            chat_id=provision.chat_id,
        )
        put_binding(binding)
        register_active_channel(
            user_id=provision.user_id,
            channel=ActiveRuntimeChannel.TELEGRAM,
        )
        presence = get_or_create_presence(binding)
        await presence.start()
        welcome = "已绑定 companion，可以直接发消息聊天。"
        if provision.is_new_user:
            welcome = "欢迎！已为你创建访客账号并绑定 companion，可以直接发中文消息。"
        return welcome
