"""SMS channel downlink: materialize and send assistant text segments.

TODO(sms-mms): #3810 — MMS inbound/outbound for image tool output (epic #3804).
TODO(sms-proactive-cap): #3806 — enforce proactive daily cap and quiet hours here or in pump (epic #3804).
"""

from __future__ import annotations

import asyncio

from app.core.companion_harness.companion.utc import (
    strip_leading_transcript_timestamp_prefixes,
)
from app.core.companion_harness.agentic_companion.output_queue import (
    ReadyOutputMessage,
    ready_output_delivers_user_visible_text,
)
from app.external_services.twilio_sms import TwilioSmsApi
from app.services.agentic_channel.adapters.sms.materialize import (
    materialize_sms_body,
)
from app.core.companion_harness.agentic_companion.types import OutputMessageKind

_SMS_TEXT_KINDS = frozenset(
    {
        OutputMessageKind.USER_REPLY,
        OutputMessageKind.PROACTIVE,
        OutputMessageKind.SCHEDULED,
        OutputMessageKind.MONOLOG,
    }
)


class SmsChannelDownlink:
    """Deliver visible assistant text via Twilio ``Messages.create``."""

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

    async def deliver(self, message: ReadyOutputMessage) -> None:
        if message.kind not in _SMS_TEXT_KINDS:
            return
        if not ready_output_delivers_user_visible_text(message):
            return
        text = strip_leading_transcript_timestamp_prefixes(message.text.strip())
        segments = materialize_sms_body(text)
        for segment in segments:
            await asyncio.to_thread(
                self._api.send_message,
                to_number=self._to_number,
                from_number=self._from_number,
                body=segment,
            )
