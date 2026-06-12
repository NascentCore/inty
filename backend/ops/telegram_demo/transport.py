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
from backend.ops.telegram_demo.binding import (
    StartPayloadKind,
    TelegramDemoBinding,
    parse_start_payload,
)
from app.services.agentic_companion.runtime_channel_registry import (
    ActiveRuntimeChannel,
    other_active_channel,
    register_active_channel,
)
from backend.ops.telegram_demo.persistence import (
    load_poll_offset,
    save_poll_offset,
)
from backend.ops.telegram_demo.provision import (
    TelegramProvisionResult,
    provision_inty_for_telegram_chat,
    provision_inty_for_telegram_onboard,
)
from backend.ops.telegram_demo.session_store import (
    get_binding,
    get_or_create_presence,
    put_binding,
    start_presence,
)


class TelegramTransport:
    """One shared-bot ``getUpdates`` loop; routes each DM to the correct companion.

    Multi-user routing (many Telegram accounts, one ``@bot`` token):

    - Telegram assigns each DM a stable ``chat_id`` (``TelegramIncomingMessage.chat_id``).
    - ``/start …`` creates or refreshes a row in the binding store:
      ``telegram_chat_id → (user_id, agent_id, chat_id)`` — one guest User and one
      Agent per teammate (v2 ``/start onboard``; legacy ``/start agent_{id}`` for tests).
    - Later text: ``get_binding(chat_id)`` → ``TelegramInprocessPresence`` for that
      scope → ``run_user_chat(user_id, agent_id, chat_id, runtime_channel=TELEGRAM)``.
    - Outbound replies use the same ``inbound.chat_id`` so messages never cross chats.

    Transport is shared; companion state (MemoryStore, inner-tick worker) is per binding.

    TODO(telegram-demo-multi-replica): single Ops process owns getUpdates; do not run
    multiple replicas with the same bot token.
    """

    def __init__(self, *, api: TelegramBotApi) -> None:
        assert api is not None
        self._api = api
        self._offset: int | None = None
        self._stop = asyncio.Event()
        self._long_poll_timeout_seconds = 30
        self._offset_loaded = False

    async def _ensure_offset_loaded(self) -> None:
        if self._offset_loaded:
            return
        self._offset = await load_poll_offset()
        self._offset_loaded = True

    async def run_until_stopped(self) -> None:
        await self._ensure_offset_loaded()
        while not self._stop.is_set():
            try:
                messages, next_offset = await asyncio.to_thread(
                    self._api.get_text_messages,
                    offset=self._offset,
                    timeout_seconds=self._long_poll_timeout_seconds,
                )
                if next_offset is not None:
                    self._offset = next_offset
                    await save_poll_offset(next_offset)
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
        """Route one inbound text update by ``inbound.chat_id`` (not by bot username)."""
        start = parse_start_payload(inbound.text)
        if start.kind == StartPayloadKind.ONBOARD:
            return await self._handle_onboard(telegram_chat_id=inbound.chat_id)
        if start.kind == StartPayloadKind.AGENT_ID:
            assert start.agent_id is not None
            return await self._handle_start(
                telegram_chat_id=inbound.chat_id,
                agent_id=start.agent_id,
            )
        binding = get_binding(inbound.chat_id)
        if binding is None:
            return (
                "请先打开 Ops /telegram-demo 页面扫码，"
                "或在对话中发送 /start onboard 完成绑定。"
            )
        presence = get_or_create_presence(binding)
        return await presence.handle_user_text(inbound.text)

    async def _handle_onboard(self, *, telegram_chat_id: str) -> str:
        existing = get_binding(telegram_chat_id)
        if existing is not None:
            return "欢迎回来！已绑定 companion，可以直接发消息聊天。"
        try:
            provision = await provision_inty_for_telegram_onboard(
                telegram_chat_id=telegram_chat_id,
            )
        except ValueError as exc:
            return str(exc)
        return await self._activate_binding(
            telegram_chat_id=telegram_chat_id,
            provision=provision,
        )

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
        return await self._activate_binding(
            telegram_chat_id=telegram_chat_id,
            provision=provision,
        )

    async def _activate_binding(
        self,
        *,
        telegram_chat_id: str,
        provision: TelegramProvisionResult,
    ) -> str:
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
        await put_binding(binding)
        register_active_channel(
            user_id=provision.user_id,
            channel=ActiveRuntimeChannel.TELEGRAM,
        )
        await start_presence(binding, api=self._api)
        if provision.is_new_user:
            return (
                "欢迎！已为你创建 companion，可以直接发中文消息。"
                "完成 bootstrap 后 companion 会更了解你。"
            )
        return "已绑定 companion，可以直接发消息聊天。"
