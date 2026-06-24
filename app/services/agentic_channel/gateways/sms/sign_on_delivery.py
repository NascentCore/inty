"""SMS sign-on greeting delivery bypassing IM-only OutputQueue presence rules.

Generated entirely by Cursor agent.

``greet_on_sign_on`` enqueues with empty ``batch_id``; ``AgentChannelPresence`` only
routes agent-initiated visible rows on IM channels (#3576). SMS flushes via gateway
downlink until harness uses ``agent-initiated:`` batch ids for all gateways.
"""

from __future__ import annotations

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.output_queue import (
    ReadyOutputMessage,
)
from app.core.companion_harness.companion.utc import (
    strip_leading_transcript_timestamp_prefixes,
)
from app.services.agentic_channel.gateways.sms.downlink import SmsGatewayDownlink
from app.services.agentic_channel.serving import flush_scope_output_queue_ready
from app.services.agentic_companion.downlink import agent_initiated_visible_downlink


async def flush_sign_on_greeting_to_sms_downlink(
    *,
    scope: AgentScope,
    downlink: SmsGatewayDownlink,
) -> None:
    """Drain ready OutputQueue rows from sign-on greeting onto SMS."""

    async def _deliver_ready(message: ReadyOutputMessage) -> None:
        text = strip_leading_transcript_timestamp_prefixes(message.text.strip())
        if not text:
            return
        await downlink.deliver(
            agent_initiated_visible_downlink(
                assistant_text=text,
                output_message=message,
            )
        )

    await flush_scope_output_queue_ready(
        scope,
        deliver_message=_deliver_ready,
    )
