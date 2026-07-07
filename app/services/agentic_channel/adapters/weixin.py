"""Weixin channel adapter for agent-channel stack."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.output_queue import (
    ReadyOutputMessage,
    ready_output_delivers_user_visible_text,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)
from app.core.companion_harness.companion.utc import (
    strip_leading_transcript_timestamp_prefixes,
)
from app.core.companion_harness.agentic_companion.types import OutputMessageKind
from app.services.agentic_companion.downlink import ChannelDownlink

WeixinAssistantTextSink = Callable[[str], Awaitable[None]]

_WEIXIN_TEXT_KINDS = frozenset(
    {
        OutputMessageKind.USER_REPLY,
        OutputMessageKind.PROACTIVE,
        OutputMessageKind.SCHEDULED,
        OutputMessageKind.MONOLOG,
    }
)


class WeixinChannelAdapter:
    """Deliver assistant text via one Weixin ``send_text`` sink."""

    def __init__(
        self,
        *,
        send_assistant_text: WeixinAssistantTextSink,
    ) -> None:
        assert send_assistant_text is not None
        self._send_assistant_text = send_assistant_text

    @property
    def channel(self) -> ChannelKind:
        return ChannelKind.WECHAT_WEIXIN

    def as_downlink(self) -> ChannelDownlink:
        return _WeixinChannelDownlink(
            send_assistant_text=self._send_assistant_text,
        )

    async def on_turn_up(self, scope: AgentScope) -> None:
        assert scope is not None

    async def on_turn_down(self, scope: AgentScope) -> None:
        assert scope is not None


class WeixinChannelAdapterStub(WeixinChannelAdapter):
    """No-op Weixin adapter for registry tests without a live transport."""

    def __init__(self) -> None:
        async def _noop(_: str) -> None:
            return None

        super().__init__(send_assistant_text=_noop)


class _WeixinChannelDownlink:
    """Deliver OutputQueue rows as plain Weixin text."""

    def __init__(self, *, send_assistant_text: WeixinAssistantTextSink) -> None:
        self._send_assistant_text = send_assistant_text

    async def deliver(self, message: ReadyOutputMessage) -> None:
        if message.kind not in _WEIXIN_TEXT_KINDS:
            return
        if not ready_output_delivers_user_visible_text(message):
            return
        text = strip_leading_transcript_timestamp_prefixes(message.text.strip())
        if not text:
            return
        await self._send_assistant_text(text)
