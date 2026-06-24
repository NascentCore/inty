"""SMS inner-tick delivery wiring for the gateway adapter.

Generated entirely by Cursor agent.

TODO(sms-plain-text-sink): Rename ``InnerTickDelivery.telegram_assistant_text`` to a
gateway-neutral plain-text sink when #3576/general gateway traits land.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.core.companion_harness.agent_channel.gateway import GatewayKind
from app.services.agentic_companion.inner_tick_delivery import InnerTickDelivery

PlainTextAssistantSink = Callable[[str], Awaitable[None]]


def sms_inner_tick_delivery(
    assistant_text: PlainTextAssistantSink,
) -> InnerTickDelivery:
    """Build inner-tick delivery for SMS using the shared plain-text sink slot."""
    assert assistant_text is not None
    # TODO(rename-plain-text-sink): ``telegram_assistant_text`` is a generic plain-text IM sink.
    return InnerTickDelivery(
        ws_outbound_queue=None,
        weixin_assistant_text=None,
        telegram_assistant_text=assistant_text,
        runtime_channel=GatewayKind.SMS,
    )
