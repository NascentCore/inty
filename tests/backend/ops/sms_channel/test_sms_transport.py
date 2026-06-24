"""SmsTransport routes inbound SMS by user phone."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import delete

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import ChannelKind
from app.db.session import AsyncSessionLocal
from app.external_services.twilio_sms import TwilioInboundSms, TwilioSmsSendResult
from app.models.agent import Agent
from app.models.companion_bond import CompanionBond
from app.models.user import User
from app.services.agentic_channel.channel_runtime import (
    clear_registries_for_tests,
    get_scope_channel_registry,
)
from app.services.agentic_channel.companion_bonds import get_companion_bond_for_scope
from app.services.agentic_channel.endpoints import resolve_scope
from app.services.agentic_channel.presence import (
    clear_presences_for_tests,
    ensure_presence,
    get_presence,
)
from backend.ops.sms_channel import session_store
from backend.ops.sms_channel.binding import SmsCommand, parse_sms_command
from backend.ops.sms_channel.transport import (
    SmsTransport,
    _EMPTY_CHAT_PROMPT,
    _ONBOARD_HINT,
)
from tests.app.services.agentic_channel.companion_test_fixtures import (
    create_guest_scope_for_test,
    delete_guest_scope_for_test,
)


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


@pytest.mark.asyncio
async def test_sms_transport_empty_chat_sends_prompt() -> None:
    clear_registries_for_tests()
    clear_presences_for_tests()
    session_store.clear_all_for_tests()
    scope = await create_guest_scope_for_test(
        channel=ChannelKind.SMS,
        nickname_prefix="SmsEmpty",
        meta_data={"agent_channel": True},
    )
    api = _FakeTwilioSmsApi()
    transport = SmsTransport(api=api, from_number="+15005550006")
    try:
        async with AsyncSessionLocal() as db:
            from app.services.agentic_channel.endpoints import upsert_endpoint_in_session

            await upsert_endpoint_in_session(
                db,
                scope,
                channel=ChannelKind.SMS,
                channel_address="+11234560999",
                channel_user_id="+11234560999",
            )
            await db.commit()
        inbound = TwilioInboundSms(
            from_e164="+11234560999",
            to_e164="+15005550006",
            body="   ",
            message_sid="SM_IN_EMPTY",
        )
        await transport.handle_inbound(inbound)
        assert api.sent[-1]["body"] == _EMPTY_CHAT_PROMPT
    finally:
        await delete_guest_scope_for_test(scope)


@pytest.mark.asyncio
async def test_sms_transport_stop_clears_presence_and_pauses_bond() -> None:
    clear_registries_for_tests()
    clear_presences_for_tests()
    session_store.clear_all_for_tests()
    scope = await create_guest_scope_for_test(
        channel=ChannelKind.SMS,
        nickname_prefix="SmsStop",
        meta_data={"agent_channel": True},
    )
    phone = f"+1123456{scope.user_id[-4:]}"
    api = _FakeTwilioSmsApi()
    transport = SmsTransport(api=api, from_number="+15005550006")
    try:
        async with AsyncSessionLocal() as db:
            from app.services.agentic_channel.endpoints import upsert_endpoint_in_session

            await upsert_endpoint_in_session(
                db,
                scope,
                channel=ChannelKind.SMS,
                channel_address=phone,
                channel_user_id=phone,
            )
            await db.commit()
        await transport._ensure_active(
            inbound=TwilioInboundSms(
                from_e164=phone,
                to_e164="+15005550006",
                body="START",
                message_sid="SM_STOP_A",
            ),
            scope=scope,
            reason="test_active",
        )
        assert get_presence(scope) is not None

        await transport.handle_inbound(
            TwilioInboundSms(
                from_e164=phone,
                to_e164="+15005550006",
                body="STOP",
                message_sid="SM_STOP_B",
            )
        )
        assert get_presence(scope) is None
        assert get_scope_channel_registry(scope).active_channel() is None
        async with AsyncSessionLocal() as db:
            bond = await get_companion_bond_for_scope(db, scope)
            assert bond is not None
            assert bond.runtime_paused_at is not None

        await transport.handle_inbound(
            TwilioInboundSms(
                from_e164=phone,
                to_e164="+15005550006",
                body="START",
                message_sid="SM_STOP_C",
            )
        )
        assert get_presence(scope) is not None
        async with AsyncSessionLocal() as db:
            bond = await get_companion_bond_for_scope(db, scope)
            assert bond is not None
            assert bond.runtime_paused_at is None
    finally:
        await delete_guest_scope_for_test(scope)
