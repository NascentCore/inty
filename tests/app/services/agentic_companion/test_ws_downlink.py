"""WebSocketDownlink queue delivery."""

from __future__ import annotations

import asyncio

import pytest

from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.tools.tool_background import ToolOutputEvent
from app.services.agentic_companion.downlink import tool_background_downlink
from app.services.agentic_companion.ws_downlink import WebSocketDownlink
from app.services.ws_session_messages import WsOutboundPayload


@pytest.mark.asyncio
async def test_ws_downlink_delivers_tool_background_payload() -> None:
    queue: asyncio.Queue[WsOutboundPayload] = asyncio.Queue()
    seen_tool: list[ToolOutputEvent] = []

    async def tool_materializer(
        tool_output: ToolOutputEvent,
    ) -> WsOutboundPayload:
        seen_tool.append(tool_output)
        return {"source": "tool_bg", "text": tool_output.text}

    downlink = WebSocketDownlink(queue, tool_materializer)
    tool_event = _tool_event(output_to_user=True, text="bg reply")
    await downlink.deliver(tool_background_downlink(tool_output=tool_event))

    assert seen_tool == [tool_event]
    payload = queue.get_nowait()
    assert payload == {"source": "tool_bg", "text": "bg reply"}


@pytest.mark.asyncio
async def test_ws_downlink_skips_suppressed_tool_background() -> None:
    queue: asyncio.Queue[WsOutboundPayload] = asyncio.Queue()
    downlink = WebSocketDownlink(queue, _fail_if_called_tool_materializer)
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
