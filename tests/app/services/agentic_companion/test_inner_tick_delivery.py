"""InnerTickDelivery: WebSocket queue vs Weixin plain text."""

from __future__ import annotations

import asyncio

import pytest

from app.services.agentic_companion.inner_tick_delivery import (
    deliver_inner_tick_assistant,
    inner_tick_delivery_for_weixin,
    inner_tick_delivery_for_ws,
)


@pytest.mark.asyncio
async def test_deliver_inner_tick_assistant_ws_puts_payload() -> None:
    queue: asyncio.Queue = asyncio.Queue()
    delivery = inner_tick_delivery_for_ws(queue)
    await deliver_inner_tick_assistant(
        delivery,
        ws_payload={"text": "hello"},
        assistant_text="hello",
    )
    assert queue.get_nowait() == {"text": "hello"}


@pytest.mark.asyncio
async def test_deliver_inner_tick_assistant_weixin_calls_sink() -> None:
    sent: list[str] = []

    async def sink(text: str) -> None:
        sent.append(text)

    delivery = inner_tick_delivery_for_weixin(sink)
    await deliver_inner_tick_assistant(
        delivery,
        ws_payload=None,
        assistant_text="  proactive hello  ",
    )
    assert sent == ["proactive hello"]


@pytest.mark.asyncio
async def test_deliver_inner_tick_assistant_weixin_skips_blank() -> None:
    sent: list[str] = []

    async def sink(text: str) -> None:
        sent.append(text)

    delivery = inner_tick_delivery_for_weixin(sink)
    await deliver_inner_tick_assistant(
        delivery,
        ws_payload=None,
        assistant_text="   ",
    )
    assert sent == []
