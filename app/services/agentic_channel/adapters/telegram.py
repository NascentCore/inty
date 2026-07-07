"""Telegram channel adapter for agent-channel stack.

TODO(telegram-meta-ops-tools): Meta-ops dispatch (setMyName, setMyDescription, …) — #3397;
  framework #3362; dedicated-bot #3361; shared-bot must not expose bot-global meta ops #3396.
TODO(telegram-reply-reaction): ``sendMessage`` reply_parameters + ``setMessageReaction`` on
  downlink; inbound reply_to / message_reaction → harness — #3441 (epic #3440)
TODO(!3451): Deliver image-bearing ``Downlink`` events through native Telegram image messages.
"""

from __future__ import annotations

import asyncio

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)
from app.core.companion_harness.companion.utc import (
    strip_leading_transcript_timestamp_prefixes,
)
from app.core.companion_harness.agentic_companion.output_queue import (
    ReadyOutputMessage,
    ready_output_delivers_user_visible_text,
)
from app.external_services.telegram_bot_api import TelegramBotApi
from app.services.agentic_companion.downlink import (
    ChannelDownlink,
    DownlinkKind,
)
from app.services.agentic_companion.inner_tick_delivery import (
    inner_tick_delivery_for_telegram,
)

_TELEGRAM_TEXT_KINDS = frozenset(
    {
        DownlinkKind.USER_REPLY,
        DownlinkKind.PROACTIVE,
        DownlinkKind.SCHEDULED,
        DownlinkKind.MONOLOG,
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
    def channel(self) -> ChannelKind:
        return ChannelKind.TELEGRAM

    def as_downlink(self) -> ChannelDownlink:
        return _TelegramChannelDownlink(
            api=self._api,
            channel_address=self._channel_address,
        )

    async def on_turn_up(self, scope: AgentScope) -> None:
        assert scope is not None

    async def on_turn_down(self, scope: AgentScope) -> None:
        assert scope is not None

    def inner_tick_delivery(self):
        downlink = self.as_downlink()

        async def send_assistant_text(text: str) -> None:
            await downlink.deliver(
                ReadyOutputMessage(
                    message_id="inner-tick-direct",
                    batch_id="inner-tick-direct",
                    kind=DownlinkKind.PROACTIVE,
                    text=text,
                    sequence=0,
                    message_ids=(),
                )
            )

        return inner_tick_delivery_for_telegram(send_assistant_text)


class _TelegramChannelDownlink:
    """Deliver text today; native image bubbles are tracked by #3451."""

    def __init__(
        self,
        *,
        api: TelegramBotApi,
        channel_address: str,
    ) -> None:
        self._api = api
        self._channel_address = channel_address

    async def deliver(self, message: ReadyOutputMessage) -> None:
        if message.kind not in _TELEGRAM_TEXT_KINDS:
            return
        if not ready_output_delivers_user_visible_text(message):
            return
        text = strip_leading_transcript_timestamp_prefixes(message.text.strip())
        if not text:
            return
        await asyncio.to_thread(
            self._api.send_message,
            chat_id=self._channel_address,
            text=text,
            parse_mode=None,
        )
