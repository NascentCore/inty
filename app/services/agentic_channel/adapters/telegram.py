"""Telegram channel adapter for agent-channel stack.

TODO(telegram-channel-tools): Per-channel tools (setMyName, setMyDescription, …) need
  dedicated-bot bonding; shared-bot must not expose bot-global meta ops — #3361
"""

from __future__ import annotations

import asyncio

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.core.companion_harness.companion.utc import (
    strip_leading_transcript_timestamp_prefixes,
)
from app.external_services.telegram_bot_api import TelegramBotApi
from app.services.agentic_companion.downlink import (
    ChannelDownlink,
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


class TelegramChannelAdapter:
    """Deliver assistant text via ``sendMessage(chat_id=channel_address)``."""

    def __init__(
        self,
        *,
        api: TelegramBotApi,
        channel_address: str,
    ) -> None:
        assert api is not None
        assert channel_address != ""
        self._api = api
        self._channel_address = channel_address

    @property
    def channel(self) -> CompanionRuntimeChannel:
        return CompanionRuntimeChannel.TELEGRAM

    def as_downlink(self) -> ChannelDownlink:
        return _TelegramChannelDownlink(
            api=self._api,
            channel_address=self._channel_address,
        )

    async def on_turn_up(self, scope: AgentScope) -> None:
        assert scope is not None

    async def on_turn_down(self, scope: AgentScope) -> None:
        assert scope is not None


class _TelegramChannelDownlink:
    def __init__(
        self,
        *,
        api: TelegramBotApi,
        channel_address: str,
    ) -> None:
        self._api = api
        self._channel_address = channel_address

    async def deliver(self, event: Downlink) -> None:
        if event.kind not in _TELEGRAM_TEXT_KINDS:
            return
        if not downlink_delivers_user_visible_text(event):
            return
        text = strip_leading_transcript_timestamp_prefixes(
            event.assistant_text.strip()
        )
        if not text:
            return
        await asyncio.to_thread(
            self._api.send_message,
            chat_id=self._channel_address,
            text=text,
        )
