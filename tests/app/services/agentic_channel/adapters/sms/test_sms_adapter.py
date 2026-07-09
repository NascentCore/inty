"""Tests for SMS channel adapter downlink."""

from __future__ import annotations

import pytest

from app.external_services.twilio_sms import TwilioSmsSendResult
from app.core.agentic_companion.output_queue import (
    ReadyOutputMessage,
)
from app.services.agentic_channel.adapters.sms.adapter import SmsChannelAdapter
from app.core.agentic_companion.types import OutputMessageKind


class _FakeTwilioSmsApi:
    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    def send_message(
        self,
        *,
        to_number: str,
        from_number: str,
        body: str,
    ) -> TwilioSmsSendResult:
        self.sent.append(
            {
                "to_number": to_number,
                "from_number": from_number,
                "body": body,
            }
        )
        return TwilioSmsSendResult(sid="SM_TEST", status="queued")


@pytest.mark.asyncio
async def test_sms_channel_downlink_delivers_proactive() -> None:
    api = _FakeTwilioSmsApi()
    adapter = SmsChannelAdapter(
        api=api,
        from_number="+15005550006",
        to_number="+11234560123",
    )
    downlink = adapter.as_downlink()
    await downlink.deliver(
        ReadyOutputMessage(
            message_id="sms-1",
            batch_id="batch-sms-1",
            kind=OutputMessageKind.PROACTIVE,
            text="Hello from Inty",
            sequence=1,
            message_ids=(),
        )
    )
    assert api.sent == [
        {
            "to_number": "+11234560123",
            "from_number": "+15005550006",
            "body": "Hello from Inty",
        }
    ]
