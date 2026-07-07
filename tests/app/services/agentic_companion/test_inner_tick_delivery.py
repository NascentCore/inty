"""InnerTickDelivery: IM plain-text sinks and pump-owned App-WS."""

from __future__ import annotations

import pytest

from app.core.companion_harness.companion.runtime_channel import ChannelKind
from app.services.agentic_companion.inner_tick_delivery import (
    InnerTickDelivery,
    deliver_inner_tick_assistant,
    inner_tick_delivery_for_pump_owned,
    inner_tick_delivery_for_telegram,
    inner_tick_delivery_for_weixin,
)


@pytest.mark.asyncio
async def test_deliver_inner_tick_assistant_weixin_skips_blank() -> None:
    sent: list[str] = []

    async def sink(text: str) -> None:
        sent.append(text)

    delivery = inner_tick_delivery_for_weixin(sink)
    await deliver_inner_tick_assistant(
        delivery,
        assistant_text="",
    )
    assert sent == []


@pytest.mark.asyncio
async def test_deliver_inner_tick_assistant_pump_owned_is_noop() -> None:
    delivery = inner_tick_delivery_for_pump_owned(ChannelKind.APP_WS)
    await deliver_inner_tick_assistant(
        delivery,
        assistant_text="hello",
    )


@pytest.mark.asyncio
async def test_deliver_inner_tick_assistant_weixin_calls_sink() -> None:
    sent: list[str] = []

    async def sink(text: str) -> None:
        sent.append(text)

    delivery = inner_tick_delivery_for_weixin(sink)
    await deliver_inner_tick_assistant(
        delivery,
        assistant_text="  proactive hello  ",
    )
    assert sent == ["proactive hello"]


@pytest.mark.asyncio
async def test_deliver_inner_tick_assistant_telegram_calls_sink() -> None:
    sent: list[str] = []

    async def sink(text: str) -> None:
        sent.append(text)

    delivery = inner_tick_delivery_for_telegram(sink)
    await deliver_inner_tick_assistant(
        delivery,
        assistant_text="  telegram proactive  ",
    )
    assert sent == ["telegram proactive"]


def test_inner_tick_delivery_rejects_multiple_im_sinks() -> None:
    async def _telegram_sink(_: str) -> None:
        return None

    async def _weixin_sink(_: str) -> None:
        return None

    with pytest.raises(AssertionError):
        InnerTickDelivery(
            weixin_assistant_text=_weixin_sink,
            telegram_assistant_text=_telegram_sink,
            runtime_channel=ChannelKind.TELEGRAM,
        )
