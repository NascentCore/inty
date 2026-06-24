"""SmsTransport routes inbound SMS by user phone."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.core.companion_harness.companion.runtime_channel import ChannelKind
from app.external_services.twilio_sms import TwilioInboundSms, TwilioSmsSendResult
from app.services.agentic_channel.channel_runtime import clear_registries_for_tests
from app.services.agentic_channel.endpoints import resolve_scope
from app.services.agentic_channel.presence import clear_presences_for_tests
from backend.ops.sms_channel import session_store
from backend.ops.sms_channel.binding import SmsCommand, parse_sms_command
from backend.ops.sms_channel.transport import SmsTransport, _ONBOARD_HINT


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


def test_parse_sms_command_start_and_stop() -> None:
    assert parse_sms_command("  START ") == SmsCommand.START
    assert parse_sms_command("stop") == SmsCommand.STOP
    assert parse_sms_command("hello") == SmsCommand.CHAT


@pytest.mark.asyncio
async def test_sms_transport_start_provisions_guest_scope() -> None:
    clear_registries_for_tests()
    clear_presences_for_tests()
    session_store.clear_all_for_tests()
    api = _FakeTwilioSmsApi()
    transport = SmsTransport(api=api, from_number="+15005550006")
    inbound = TwilioInboundSms(
        from_e164="+11234560123",
        to_e164="+15005550006",
        body="START",
        message_sid="SM_IN_1",
    )
    with patch(
        "app.services.agentic_channel.presence.get_presence",
    ) as get_presence_mock:
        mock_presence = AsyncMock()
        mock_presence.greet_on_sign_on = AsyncMock()
        get_presence_mock.return_value = mock_presence
        await transport.handle_inbound(inbound)
    scope = await resolve_scope(
        channel=ChannelKind.SMS,
        channel_address="+11234560123",
    )
    assert scope is not None
    assert api.sent


@pytest.mark.asyncio
async def test_sms_transport_unbound_chat_sends_hint() -> None:
    clear_registries_for_tests()
    clear_presences_for_tests()
    session_store.clear_all_for_tests()
    api = _FakeTwilioSmsApi()
    transport = SmsTransport(api=api, from_number="+15005550006")
    inbound = TwilioInboundSms(
        from_e164="+19998887777",
        to_e164="+15005550006",
        body="hello",
        message_sid="SM_IN_2",
    )
    await transport.handle_inbound(inbound)
    assert api.sent[-1]["body"] == _ONBOARD_HINT
