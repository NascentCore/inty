"""How inner-tick turns reach the human on WebSocket, Weixin, or Telegram.

v1: direct delivery (``deliver_visible_inner_tick_turn``). TODO(!3489): proactive via OutputQueue + shared pump (!3485).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.core.companion_harness.companion.models import (
    user_visible_assistant_text,
)

WeixinAssistantTextSink = Callable[[str], Awaitable[None]]
TelegramAssistantTextSink = Callable[[str], Awaitable[None]]


@dataclass(frozen=True)
class InnerTickDelivery:
    """Which medium should carry a companion-initiated message to the user right now.

    Inner ticks (reminders, proactive outreach, quiet maintenance) are the same on the
    companion side whether the human is in the app, on WeChat, or on Telegram; this
    value only picks the outward-facing shape. One presence session uses one medium
    at a time—never more than one.
    """

    ws_outbound_queue: asyncio.Queue | None
    weixin_assistant_text: WeixinAssistantTextSink | None
    telegram_assistant_text: TelegramAssistantTextSink | None
    runtime_channel: CompanionRuntimeChannel

    def __post_init__(self) -> None:
        count = sum(
            medium is not None
            for medium in (
                self.ws_outbound_queue,
                self.weixin_assistant_text,
                self.telegram_assistant_text,
            )
        )
        assert count == 1


async def deliver_inner_tick_assistant(
    delivery: InnerTickDelivery,
    *,
    ws_payload: dict | None,
    assistant_text: str,
) -> None:
    """Push a full WS frame and/or plain channel text after history is persisted."""
    visible = user_visible_assistant_text(assistant_text)
    if visible is None:
        return
    # TODO(companion-ws-inner-tick-downlink): enqueue via WebSocketDownlink.deliver, not raw put. #3210 #3398
    if delivery.ws_outbound_queue is not None:
        assert ws_payload is not None
        await delivery.ws_outbound_queue.put(ws_payload)
    if delivery.weixin_assistant_text is not None:
        await delivery.weixin_assistant_text(visible)
    if delivery.telegram_assistant_text is not None:
        await delivery.telegram_assistant_text(visible)


def inner_tick_delivery_for_ws(
    outbound_queue: asyncio.Queue,
) -> InnerTickDelivery:
    assert outbound_queue is not None
    return InnerTickDelivery(
        ws_outbound_queue=outbound_queue,
        weixin_assistant_text=None,
        telegram_assistant_text=None,
        runtime_channel=CompanionRuntimeChannel.APP,
    )


def inner_tick_delivery_for_weixin(
    assistant_text: WeixinAssistantTextSink,
) -> InnerTickDelivery:
    assert assistant_text is not None
    return InnerTickDelivery(
        ws_outbound_queue=None,
        weixin_assistant_text=assistant_text,
        telegram_assistant_text=None,
        runtime_channel=CompanionRuntimeChannel.WECHAT_WEIXIN,
    )


def inner_tick_delivery_for_telegram(
    assistant_text: TelegramAssistantTextSink,
) -> InnerTickDelivery:
    assert assistant_text is not None
    return InnerTickDelivery(
        ws_outbound_queue=None,
        weixin_assistant_text=None,
        telegram_assistant_text=assistant_text,
        runtime_channel=CompanionRuntimeChannel.TELEGRAM,
    )
