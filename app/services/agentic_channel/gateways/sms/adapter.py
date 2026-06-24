"""SMS gateway adapter for the agent-channel stack.

Generated entirely by Cursor agent.
"""

from __future__ import annotations

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agent_channel.gateway import GatewayKind
from app.external_services.twilio_sms import TwilioSmsApi
from app.services.agentic_channel.gateways.sms.downlink import SmsGatewayDownlink
from app.services.agentic_channel.gateways.sms.inner_tick import sms_inner_tick_delivery
from app.services.agentic_companion.downlink import (
    ChannelDownlink,
    Downlink,
    DownlinkKind,
)


class SmsGatewayAdapter:
    """Deliver assistant text via Twilio SMS to one bonded E.164 number."""

    def __init__(
        self,
        *,
        api: TwilioSmsApi,
        from_number: str,
        to_number: str,
    ) -> None:
        assert api is not None
        assert from_number != ""
        assert to_number != ""
        self._api = api
        self._from_number = from_number
        self._to_number = to_number

    @property
    def channel(self) -> GatewayKind:
        return GatewayKind.SMS

    def as_downlink(self) -> ChannelDownlink:
        return SmsGatewayDownlink(
            api=self._api,
            from_number=self._from_number,
            to_number=self._to_number,
        )

    async def on_turn_up(self, scope: AgentScope) -> None:
        assert scope is not None

    async def on_turn_down(self, scope: AgentScope) -> None:
        assert scope is not None

    def inner_tick_delivery(self):
        downlink = self.as_downlink()

        async def send_assistant_text(text: str) -> None:
            await downlink.deliver(
                Downlink(
                    kind=DownlinkKind.PROACTIVE,
                    assistant_text=text,
                    turn=None,
                    tool_output=None,
                    bootstrap_interim=None,
                    scheduled_task_id=None,
                    transcript_user_text=None,
                )
            )

        return sms_inner_tick_delivery(send_assistant_text)
