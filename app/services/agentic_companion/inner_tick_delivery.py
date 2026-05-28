"""How inner-tick turns reach the human on WebSocket vs Weixin."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

WeixinAssistantTextSink = Callable[[str], Awaitable[None]]


@dataclass(frozen=True)
class InnerTickDelivery:
    """Which medium should carry a companion-initiated message to the user right now.

    Inner ticks (reminders, proactive outreach, quiet maintenance) are the same on the
    companion side whether the human is in the app or on WeChat; this value only picks the
    outward-facing shape. One presence session uses one medium at a time—never both.

    - App (WebSocket): the user should see it like a normal in-chat assistant turn.
    - WeChat: the user should see plain assistant text in the DM thread; silence if there is
      nothing worth saying aloud.
    """

    ws_outbound_queue: asyncio.Queue | None
    weixin_assistant_text: WeixinAssistantTextSink | None

    def __post_init__(self) -> None:
        ws = self.ws_outbound_queue is not None
        wx = self.weixin_assistant_text is not None
        assert ws ^ wx


async def deliver_inner_tick_assistant(
    delivery: InnerTickDelivery,
    *,
    ws_payload: dict | None,
    assistant_text: str,
) -> None:
    """Push a full WS frame and/or plain Weixin DM text after history is persisted."""
    # TODO(companion-ws-inner-tick-downlink): enqueue via WebSocketDownlink.deliver, not raw put. #3210
    if delivery.ws_outbound_queue is not None:
        assert ws_payload is not None
        await delivery.ws_outbound_queue.put(ws_payload)
    if delivery.weixin_assistant_text is not None:
        stripped = assistant_text.strip()
        if stripped:
            await delivery.weixin_assistant_text(stripped)


def inner_tick_delivery_for_ws(
    outbound_queue: asyncio.Queue,
) -> InnerTickDelivery:
    assert outbound_queue is not None
    return InnerTickDelivery(
        ws_outbound_queue=outbound_queue,
        weixin_assistant_text=None,
    )


def inner_tick_delivery_for_weixin(
    assistant_text: WeixinAssistantTextSink,
) -> InnerTickDelivery:
    assert assistant_text is not None
    return InnerTickDelivery(
        ws_outbound_queue=None,
        weixin_assistant_text=assistant_text,
    )
