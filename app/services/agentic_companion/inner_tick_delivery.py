"""How inner-tick turns reach the human on Weixin or Telegram.

App-WS delivery is pump-owned via OutputQueue; IM channels without presence
may still use direct text sinks until Phase 3 Weixin transport converges.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)
from app.core.companion_harness.companion.models import (
    user_visible_assistant_text,
)

WeixinAssistantTextSink = Callable[[str], Awaitable[None]]
TelegramAssistantTextSink = Callable[[str], Awaitable[None]]


@dataclass(frozen=True)
class InnerTickDelivery:
    """Which medium should carry a companion-initiated message to the user right now.

    Inner ticks (reminders, proactive outreach, quiet monolog) are the same on the
    companion side whether the human is in the app, on WeChat, or on Telegram; this
    value only picks the outward-facing shape. App-WS uses OutputQueue pump delivery
    (no direct sink). At most one IM text sink is active.
    """

    weixin_assistant_text: WeixinAssistantTextSink | None
    telegram_assistant_text: TelegramAssistantTextSink | None
    runtime_channel: ChannelKind

    def __post_init__(self) -> None:
        count = sum(
            medium is not None
            for medium in (
                self.weixin_assistant_text,
                self.telegram_assistant_text,
            )
        )
        assert count <= 1


async def deliver_inner_tick_assistant(
    delivery: InnerTickDelivery,
    *,
    assistant_text: str,
) -> None:
    """Push plain channel text after history is persisted (IM channels only)."""
    visible = user_visible_assistant_text(assistant_text)
    if visible is None:
        return
    if delivery.weixin_assistant_text is not None:
        await delivery.weixin_assistant_text(visible)
    if delivery.telegram_assistant_text is not None:
        await delivery.telegram_assistant_text(visible)


def inner_tick_delivery_for_pump_owned(
    runtime_channel: ChannelKind,
) -> InnerTickDelivery:
    """App-WS (and future pump-only channels): no direct inner-tick sink."""
    assert runtime_channel is not None
    return InnerTickDelivery(
        weixin_assistant_text=None,
        telegram_assistant_text=None,
        runtime_channel=runtime_channel,
    )


def inner_tick_delivery_for_weixin(
    assistant_text: WeixinAssistantTextSink,
) -> InnerTickDelivery:
    assert assistant_text is not None
    return InnerTickDelivery(
        weixin_assistant_text=assistant_text,
        telegram_assistant_text=None,
        runtime_channel=ChannelKind.WECHAT_WEIXIN,
    )


def inner_tick_delivery_for_telegram(
    assistant_text: TelegramAssistantTextSink,
) -> InnerTickDelivery:
    assert assistant_text is not None
    return InnerTickDelivery(
        weixin_assistant_text=None,
        telegram_assistant_text=assistant_text,
        runtime_channel=ChannelKind.TELEGRAM,
    )
