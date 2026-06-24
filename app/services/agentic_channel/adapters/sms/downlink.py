"""SMS channel downlink: materialize and send assistant text segments."""

from __future__ import annotations

import asyncio

from app.core.companion_harness.companion.utc import (
    strip_leading_transcript_timestamp_prefixes,
)
from app.external_services.twilio_sms import TwilioSmsApi
from app.services.agentic_channel.adapters.sms.materialize import (
    materialize_sms_body,
)
from app.services.agentic_companion.downlink import (
    Downlink,
    DownlinkKind,
    downlink_delivers_user_visible_text,
)

_SMS_TEXT_KINDS = frozenset(
    {
        DownlinkKind.USER_REPLY,
        DownlinkKind.PROACTIVE,
        DownlinkKind.SCHEDULED,
        DownlinkKind.MONOLOG,
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

    async def deliver(self, event: Downlink) -> None:
        if event.kind not in _SMS_TEXT_KINDS:
            return
        if not downlink_delivers_user_visible_text(event):
            return
        text = strip_leading_transcript_timestamp_prefixes(
            event.assistant_text.strip()
        )
        segments = materialize_sms_body(text)
        for segment in segments:
            await asyncio.to_thread(
                self._api.send_message,
                to_number=self._to_number,
                from_number=self._from_number,
                body=segment,
            )
