"""Tests for SMS channel adapter downlink."""

from __future__ import annotations

import pytest

from app.external_services.twilio_sms import TwilioSmsSendResult
from app.services.agentic_channel.adapters.sms.adapter import SmsChannelAdapter
from app.services.agentic_companion.downlink import Downlink, DownlinkKind


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
        Downlink(
            kind=DownlinkKind.PROACTIVE,
            assistant_text="Hello from Inty",
            turn=None,
            tool_output=None,
            bootstrap_interim=None,
            scheduled_task_id=None,
            transcript_user_text=None,
        )
    )
    assert api.sent == [
        {
            "to_number": "+11234560123",
            "from_number": "+15005550006",
            "body": "Hello from Inty",
        }
    ]
