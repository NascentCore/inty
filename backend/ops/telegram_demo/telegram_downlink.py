"""Telegram Bot API downlink: companion assistant text → ``sendMessage``."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from app.external_services.telegram_bot_api import TelegramBotApi
from app.services.agentic_companion.downlink import (
    Downlink,
    DownlinkKind,
    downlink_delivers_user_visible_text,
)

_TELEGRAM_TEXT_KINDS = frozenset(
    {
        DownlinkKind.USER_REPLY,
        DownlinkKind.PROACTIVE,
        DownlinkKind.SCHEDULED,
        DownlinkKind.MAINTENANCE,
    }
)

TelegramChatIdResolver = Callable[[], str | None]


class TelegramDownlink:
    """Deliver companion downlink events as Telegram DM text."""

    def __init__(
        self,
        *,
        api: TelegramBotApi,
        chat_id_resolver: TelegramChatIdResolver,
    ) -> None:
        assert api is not None
        assert chat_id_resolver is not None
        self._api = api
        self._chat_id_resolver = chat_id_resolver

    async def send_assistant_text(self, text: str) -> None:
        """Push plain assistant text to the bound Telegram chat."""
        stripped = text.strip()
        if not stripped:
            return
        chat_id = self._chat_id_resolver()
        if chat_id is None:
            return
        await asyncio.to_thread(
            self._api.send_message,
            chat_id=chat_id,
            text=stripped,
        )

    async def deliver(self, event: Downlink) -> None:
        if event.kind not in _TELEGRAM_TEXT_KINDS:
            return
        if not downlink_delivers_user_visible_text(event):
            return
        await self.send_assistant_text(event.assistant_text)
