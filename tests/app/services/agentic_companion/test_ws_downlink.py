"""WebSocketDownlink queue delivery."""

from __future__ import annotations

import asyncio

import pytest

from app.core.companion_harness.companion.models import CompanionTurnResult
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.tools.tool_background import ToolOutputEvent
from app.services.agentic_companion.downlink import (
    Downlink,
    DownlinkKind,
    user_reply_downlink,
)
from app.services.agentic_companion.downlink import tool_background_downlink
from app.services.agentic_companion.ws_downlink import WebSocketDownlink
from app.services.ws_session_messages import WsOutboundPayload


@pytest.mark.asyncio
async def test_ws_downlink_delivers_tool_background_payload() -> None:
    queue: asyncio.Queue[WsOutboundPayload] = asyncio.Queue()
    seen_tool: list[ToolOutputEvent] = []

    async def tool_materializer(tool_output: ToolOutputEvent) -> WsOutboundPayload:
        seen_tool.append(tool_output)
        return {"source": "tool_bg", "text": tool_output.text}

    downlink = WebSocketDownlink(
        queue,
        tool_materializer,
        bootstrap_interim_materializer=None,
        loop_foreground_materializer=None,
        deliver_ctx=None,
    )
    tool_event = _tool_event(output_to_user=True, text="bg reply")
    await downlink.deliver(tool_background_downlink(tool_output=tool_event))

    assert seen_tool == [tool_event]
    payload = queue.get_nowait()
    assert payload == {"source": "tool_bg", "text": "bg reply"}


@pytest.mark.asyncio
async def test_ws_downlink_delivers_loop_foreground_via_materializer() -> None:
    queue: asyncio.Queue[WsOutboundPayload] = asyncio.Queue()
    seen: list[tuple[Downlink, object]] = []

    async def loop_fg_materializer(
        event: Downlink,
        ctx: object,
    ) -> None:
        seen.append((event, ctx))
        await queue.put({"source": "loop_fg", "text": event.assistant_text})

    turn = CompanionTurnResult(assistant_text="hello")
    downlink = WebSocketDownlink(
        queue,
        _fail_if_called_tool_materializer,
        bootstrap_interim_materializer=None,
        loop_foreground_materializer=loop_fg_materializer,
        deliver_ctx=object(),
    )
    event = user_reply_downlink(turn=turn)
    assert event.kind is DownlinkKind.USER_REPLY
    await downlink.deliver(event)

    assert len(seen) == 1
    assert seen[0][0].assistant_text == "hello"
    payload = queue.get_nowait()
    assert payload == {"source": "loop_fg", "text": "hello"}


@pytest.mark.asyncio
async def test_ws_downlink_skips_loop_foreground_without_ctx() -> None:
    queue: asyncio.Queue[WsOutboundPayload] = asyncio.Queue()

    async def loop_fg_materializer(event: Downlink, ctx: object) -> None:
        raise AssertionError("must not run without deliver_ctx")

    turn = CompanionTurnResult(assistant_text="x")
    downlink = WebSocketDownlink(
        queue,
        _fail_if_called_tool_materializer,
        bootstrap_interim_materializer=None,
        loop_foreground_materializer=loop_fg_materializer,
        deliver_ctx=None,
    )
    await downlink.deliver(user_reply_downlink(turn=turn))
    assert queue.empty()


@pytest.mark.asyncio
async def test_ws_downlink_skips_suppressed_tool_background() -> None:
    queue: asyncio.Queue[WsOutboundPayload] = asyncio.Queue()
    downlink = WebSocketDownlink(
        queue,
        _fail_if_called_tool_materializer,
        bootstrap_interim_materializer=None,
        loop_foreground_materializer=None,
        deliver_ctx=None,
    )
    tool_event = _tool_event(output_to_user=False, text="hidden")
    await downlink.deliver(tool_background_downlink(tool_output=tool_event))
    assert queue.empty()


async def _fail_if_called_tool_materializer(
    tool_output: ToolOutputEvent,
) -> WsOutboundPayload:
    raise AssertionError("materializer must not run for suppressed tool_bg")


def _tool_event(*, output_to_user: bool, text: str) -> ToolOutputEvent:
    store = MemoryStore(
        scope=CompanionScope("u", "a", "c"),
        repository=None,
    )
    return ToolOutputEvent(
        scope_registry_key="k",
        memory_store=store,
        user_msg_uuid="u",
        assistant_msg_uuid="a",
        text=text,
        ts="",
        elapsed_ms=0,
        output_to_user=output_to_user,
    )
