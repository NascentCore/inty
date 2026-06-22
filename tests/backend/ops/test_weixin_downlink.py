"""WeixinDownlink text forwarding."""

from __future__ import annotations

import pytest

from app.core.companion_harness.companion.models import CompanionTurnResult
from app.services.agentic_companion.downlink import (
    bootstrap_interim_downlink,
    proactive_downlink,
    tool_background_downlink,
)
from app.core.companion_harness.companion.turn_routes import (
    BootstrapInterimOutput,
)
from backend.ops.weixin_channel.weixin_downlink import WeixinDownlink


@pytest.mark.asyncio
async def test_weixin_downlink_send_assistant_text_without_downlink_event() -> (
    None
):
    transport = _RecordingWeixinTransport()
    downlink = WeixinDownlink(transport, lambda: "peer-9")
    await downlink.send_assistant_text("inner tick line")
    assert transport.sent == [("peer-9", "inner tick line")]


@pytest.mark.asyncio
async def test_weixin_downlink_send_assistant_text_drops_without_peer_id() -> (
    None
):
    transport = _RecordingWeixinTransport()
    downlink = WeixinDownlink(transport, lambda: None)
    await downlink.send_assistant_text("lost")
    assert transport.sent == []


@pytest.mark.asyncio
async def test_weixin_downlink_sends_user_visible_text() -> None:
    transport = _RecordingWeixinTransport()
    downlink = WeixinDownlink(transport, lambda: "peer-1")
    turn = CompanionTurnResult(assistant_text="hello from inty")
    await downlink.deliver(
        proactive_downlink(turn=turn, transcript_user_text="（心跳）")
    )
    assert transport.sent == [("peer-1", "hello from inty")]


@pytest.mark.asyncio
async def test_weixin_downlink_skips_without_peer_id() -> None:
    transport = _RecordingWeixinTransport()
    downlink = WeixinDownlink(transport, lambda: None)
    turn = CompanionTurnResult(assistant_text="hello")
    await downlink.deliver(
        proactive_downlink(turn=turn, transcript_user_text="（心跳）")
    )
    assert transport.sent == []


@pytest.mark.asyncio
async def test_weixin_downlink_skips_bootstrap_interim() -> None:
    transport = _RecordingWeixinTransport()
    downlink = WeixinDownlink(transport, lambda: "peer-1")
    interim = BootstrapInterimOutput(
        text="round one",
        user_msg_uuid="u",
        trace_id="t",
        langsmith_trace_id="",
        langsmith_run_id="",
        round_index=1,
        had_tool_calls=True,
        assistant_msg_uuid="a",
    )
    await downlink.deliver(bootstrap_interim_downlink(interim=interim))
    assert transport.sent == []


@pytest.mark.asyncio
async def test_weixin_downlink_skips_empty_proactive() -> None:
    transport = _RecordingWeixinTransport()
    downlink = WeixinDownlink(transport, lambda: "peer-1")
    turn = CompanionTurnResult(assistant_text="")
    await downlink.deliver(
        proactive_downlink(turn=turn, transcript_user_text="（心跳）")
    )
    assert transport.sent == []


@pytest.mark.asyncio
async def test_weixin_downlink_skips_suppressed_tool_background() -> None:
    from app.core.companion_harness.companion.scope import CompanionScope
    from app.core.companion_harness.memory.memory_store import MemoryStore
    from app.core.companion_harness.tools.tool_background import ToolOutputEvent

    store = MemoryStore(
        scope=CompanionScope("u", "a", "c"),
        repository=None,
    )
    tool_event = ToolOutputEvent(
        scope_registry_key="k",
        memory_store=store,
        user_msg_uuid="u",
        assistant_msg_uuid="a",
        text="secret",
        ts="",
        elapsed_ms=0,
        output_to_user=False,
    )
    transport = _RecordingWeixinTransport()
    downlink = WeixinDownlink(transport, lambda: "peer-1")
    await downlink.deliver(tool_background_downlink(tool_output=tool_event))
    assert transport.sent == []


class _RecordingWeixinTransport:
    """Capture ``send_text`` calls for assertions."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_text(self, peer_id: str, text: str) -> None:
        self.sent.append((peer_id, text))
