"""InnerTickDelivery: WebSocket queue vs Weixin plain text."""

from __future__ import annotations

import asyncio

import pytest

from app.services.agentic_companion.inner_tick_delivery import (
    deliver_inner_tick_assistant,
    inner_tick_delivery_for_telegram,
    inner_tick_delivery_for_weixin,
    inner_tick_delivery_for_ws,
)


@pytest.mark.asyncio
async def test_deliver_inner_tick_assistant_weixin_skips_blank() -> None:
    sent: list[str] = []

    async def sink(text: str) -> None:
        sent.append(text)

    delivery = inner_tick_delivery_for_weixin(sink)
    await deliver_inner_tick_assistant(
        delivery,
        ws_payload=None,
        assistant_text="",
    )
    assert sent == []


@pytest.mark.asyncio
async def test_deliver_inner_tick_assistant_ws_skips_blank() -> None:
    queue: asyncio.Queue = asyncio.Queue()
    delivery = inner_tick_delivery_for_ws(queue)
    await deliver_inner_tick_assistant(
        delivery,
        ws_payload={"text": ""},
        assistant_text="",
    )
    assert queue.empty()


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


@pytest.mark.asyncio
async def test_deliver_inner_tick_assistant_telegram_skips_blank() -> None:
    sent: list[str] = []

    async def sink(text: str) -> None:
        sent.append(text)

    delivery = inner_tick_delivery_for_telegram(sink)
    await deliver_inner_tick_assistant(
        delivery,
        ws_payload=None,
        assistant_text="",
    )
    assert sent == []


@pytest.mark.asyncio
async def test_deliver_inner_tick_assistant_telegram_calls_sink() -> None:
    sent: list[str] = []

    async def sink(text: str) -> None:
        sent.append(text)

    delivery = inner_tick_delivery_for_telegram(sink)
    await deliver_inner_tick_assistant(
        delivery,
        ws_payload=None,
        assistant_text="  telegram proactive  ",
    )
    assert sent == ["telegram proactive"]


def test_inner_tick_delivery_rejects_multiple_media() -> None:
    import pytest

    from app.core.companion_harness.agent_channel.gateway import (
        GatewayKind,
    )
    from app.services.agentic_companion.inner_tick_delivery import (
        InnerTickDelivery,
    )

    async def _telegram_sink(_: str) -> None:
        return None

    with pytest.raises(AssertionError):
        InnerTickDelivery(
            ws_outbound_queue=asyncio.Queue(),
            weixin_assistant_text=None,
            telegram_assistant_text=_telegram_sink,
            runtime_channel=GatewayKind.TELEGRAM,
        )
