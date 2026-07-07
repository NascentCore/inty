"""SMS channel adapter for the agent-channel stack.

Generated entirely by Cursor agent.
"""

from __future__ import annotations

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import ChannelKind
from app.external_services.twilio_sms import TwilioSmsApi
from app.services.agentic_channel.adapters.sms.downlink import (
    SmsChannelDownlink,
)
from app.services.agentic_companion.downlink import ChannelDownlink


class SmsChannelAdapter:
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
    def channel(self) -> ChannelKind:
        return ChannelKind.SMS

    def as_downlink(self) -> ChannelDownlink:
        return SmsChannelDownlink(
            api=self._api,
            from_number=self._from_number,
            to_number=self._to_number,
        )

    async def on_turn_up(self, scope: AgentScope) -> None:
        assert scope is not None

    async def on_turn_down(self, scope: AgentScope) -> None:
        assert scope is not None
