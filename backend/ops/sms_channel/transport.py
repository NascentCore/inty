"""SMS gateway inbound transport for Ops Twilio webhooks.

Generated entirely by Cursor agent.

Shared long code routes by user ``From`` E.164; ``channel_address`` stores the user phone.
"""

from __future__ import annotations

import asyncio

from loguru import logger

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import ChannelKind
from app.db.session import AsyncSessionLocal
from app.external_services.twilio_sms import TwilioInboundSms, TwilioSmsApi
from app.services.agentic_channel.channel_runtime import (
    turn_channel_down,
    turn_channel_up,
)
from app.services.agentic_channel.companion_bonds import (
    get_companion_bond_for_scope,
    require_active_companion_bond,
    resume_companion_bond_runtime,
)
from app.services.agentic_channel.endpoints import (
    EndpointRecord,
    assert_inbound_endpoint_identity,
    resolve_scope,
)
from app.services.agentic_channel.errors import (
    ChannelEndpointConflictError,
    CompanionBondInvariantError,
)
from app.services.agentic_channel.gateways.sms.adapter import SmsGatewayAdapter
from app.services.agentic_channel.gateways.sms.sign_on_delivery import (
    flush_sign_on_greeting_to_sms_downlink,
)
from app.services.agentic_channel.presence import ensure_presence, get_presence
from app.services.agentic_channel.provision import (
    ChannelProvisionResult,
    provision_agent_for_channel_onboard,
)
from backend.ops.sms_channel.binding import SmsCommand, parse_sms_command
from backend.ops.sms_channel.session_store import (
    activate_sms_scope,
    remember_scope,
)

_ONBOARD_NOTICE_NEW = "Your agent is waking up and will text you soon."
_ONBOARD_NOTICE_RETURNING = (
    "Welcome back. Your companion is ready — send a message anytime."
)
_ONBOARD_HINT = "Text START to connect your Inty companion on SMS."
_IDENTITY_MISMATCH = (
    "This phone number does not match our records. "
    "Please use the same number you used when connecting."
)
_BOND_UNAVAILABLE = (
    "We couldn't reconnect your companion. "
    "Please try again later or contact support."
)
_STOP_CONFIRMATION = "You have been unsubscribed from SMS. Text START to reconnect."
# TODO(sms-proactive-cap): Add daily cap + quiet hours before prod SMS proactive rollout.


class SmsTransport:
    """Route Twilio inbound SMS into the agent-channel serving pipeline."""

    def __init__(
        self,
        *,
        api: TwilioSmsApi,
        from_number: str,
    ) -> None:
        assert api is not None
        assert from_number != ""
        self._api = api
        self._from_number = from_number

    @property
    def api(self) -> TwilioSmsApi:
        return self._api

    async def handle_inbound(self, inbound: TwilioInboundSms) -> None:
        """Process one inbound SMS asynchronously after webhook ACK."""
        if inbound.to_e164 != self._from_number:
            logger.warning(
                "sms inbound to mismatch expected={} actual={} from={}",
                self._from_number,
                inbound.to_e164,
                inbound.from_e164,
            )
            return
        command = parse_sms_command(inbound.body)
        match command:
            case SmsCommand.START:
                await self._handle_onboard(inbound=inbound)
            case SmsCommand.STOP:
                await self._handle_stop(inbound=inbound)
            case SmsCommand.CHAT:
                await self._handle_chat(inbound=inbound)

    async def _send_platform_sms(
        self,
        *,
        to_number: str,
        text: str,
    ) -> None:
        assert to_number != ""
        assert text != ""
        await asyncio.to_thread(
            self._api.send_message,
            to_number=to_number,
            from_number=self._from_number,
            body=text,
        )

    async def _handle_chat(self, *, inbound: TwilioInboundSms) -> None:
        scope = await resolve_scope(
            channel=ChannelKind.SMS,
            channel_address=inbound.from_e164,
        )
        if scope is None:
            await self._send_platform_sms(
                to_number=inbound.from_e164,
                text=_ONBOARD_HINT,
            )
            return
        try:
            await assert_inbound_endpoint_identity(
                channel=ChannelKind.SMS,
                channel_address=inbound.from_e164,
                channel_user_id=inbound.from_e164,
            )
        except ChannelEndpointConflictError:
            await self._send_platform_sms(
                to_number=inbound.from_e164,
                text=_IDENTITY_MISMATCH,
            )
            return
        await self._resume_if_paused(scope=scope)
        await self._ensure_active(
            inbound=inbound,
            scope=scope,
            reason="inbound_message",
        )
        presence = get_presence(scope)
        if presence is None:
            presence = await ensure_presence(scope)
        channel_error = await presence.handle_user_text(
            inbound.body,
            runtime_channel=ChannelKind.SMS,
        )
        if channel_error:
            await self._send_platform_sms(
                to_number=inbound.from_e164,
                text=channel_error,
            )

    async def _handle_stop(self, *, inbound: TwilioInboundSms) -> None:
        scope = await resolve_scope(
            channel=ChannelKind.SMS,
            channel_address=inbound.from_e164,
        )
        if scope is None:
            await self._send_platform_sms(
                to_number=inbound.from_e164,
                text=_STOP_CONFIRMATION,
            )
            return
        presence = get_presence(scope)
        if presence is not None:
            await presence.stop()
        await turn_channel_down(scope, ChannelKind.SMS, reason="sms_stop")
        await self._send_platform_sms(
            to_number=inbound.from_e164,
            text=_STOP_CONFIRMATION,
        )

    async def _handle_onboard(self, *, inbound: TwilioInboundSms) -> None:
        existing = await resolve_scope(
            channel=ChannelKind.SMS,
            channel_address=inbound.from_e164,
        )
        if existing is not None:
            try:
                await assert_inbound_endpoint_identity(
                    channel=ChannelKind.SMS,
                    channel_address=inbound.from_e164,
                    channel_user_id=inbound.from_e164,
                )
            except ChannelEndpointConflictError:
                await self._send_platform_sms(
                    to_number=inbound.from_e164,
                    text=_IDENTITY_MISMATCH,
                )
                return
            if not await self._gate_onboard_bond(scope=existing, inbound=inbound):
                return
            await self._resume_if_paused(scope=existing)
            await self._ensure_active(
                inbound=inbound,
                scope=existing,
                reason="onboard_returning",
            )
            await self._send_platform_sms(
                to_number=inbound.from_e164,
                text=_ONBOARD_NOTICE_RETURNING,
            )
            return
        try:
            provision = await provision_agent_for_channel_onboard(
                channel=ChannelKind.SMS,
                channel_address=inbound.from_e164,
                channel_user_id=inbound.from_e164,
            )
        except CompanionBondInvariantError:
            await self._send_platform_sms(
                to_number=inbound.from_e164,
                text=_BOND_UNAVAILABLE,
            )
            return
        except (ValueError, ChannelEndpointConflictError) as exc:
            await self._send_platform_sms(
                to_number=inbound.from_e164,
                text=str(exc),
            )
            return
        if not provision.is_new_user:
            if not await self._gate_onboard_bond(
                scope=provision.scope,
                inbound=inbound,
            ):
                return
            await self._resume_if_paused(scope=provision.scope)
            await self._ensure_active(
                inbound=inbound,
                scope=provision.scope,
                reason="onboard_returning",
            )
            await self._send_platform_sms(
                to_number=inbound.from_e164,
                text=_ONBOARD_NOTICE_RETURNING,
            )
            return
        await self._activate_provision(
            inbound=inbound,
            provision=provision,
        )

    async def _activate_provision(
        self,
        *,
        inbound: TwilioInboundSms,
        provision: ChannelProvisionResult,
    ) -> None:
        if not await self._gate_onboard_bond(
            scope=provision.scope,
            inbound=inbound,
        ):
            return
        record = EndpointRecord(
            user_id=provision.scope.user_id,
            agent_id=provision.scope.agent_id,
            channel=ChannelKind.SMS,
            channel_address=provision.channel_address,
            channel_user_id=provision.channel_user_id,
        )
        await activate_sms_scope(
            record=record,
            api=self._api,
            from_number=self._from_number,
            reason="onboard",
        )
        presence = get_presence(provision.scope)
        if presence is None:
            presence = await ensure_presence(provision.scope)
        await self._send_platform_sms(
            to_number=inbound.from_e164,
            text=_ONBOARD_NOTICE_NEW,
        )
        try:
            await presence.greet_on_sign_on(runtime_channel=ChannelKind.SMS)
            adapter = SmsGatewayAdapter(
                api=self._api,
                from_number=self._from_number,
                to_number=inbound.from_e164,
            )
            await flush_sign_on_greeting_to_sms_downlink(
                scope=provision.scope,
                downlink=adapter.as_downlink(),
            )
        except Exception:
            logger.exception(
                "sms onboard greeting failed from={} user_id={} agent_id={}",
                inbound.from_e164,
                provision.scope.user_id,
                provision.scope.agent_id,
            )

    async def _gate_onboard_bond(
        self,
        *,
        scope: AgentScope,
        inbound: TwilioInboundSms,
    ) -> bool:
        try:
            async with AsyncSessionLocal() as db:
                await require_active_companion_bond(db, scope)
        except CompanionBondInvariantError:
            await self._send_platform_sms(
                to_number=inbound.from_e164,
                text=_BOND_UNAVAILABLE,
            )
            return False
        return True

    async def _resume_if_paused(self, *, scope: AgentScope) -> None:
        async with AsyncSessionLocal() as db:
            bond = await get_companion_bond_for_scope(db, scope)
            if bond is None or bond.runtime_paused_at is None:
                return
            resumed = await resume_companion_bond_runtime(db, scope)
            if not resumed:
                return
            await db.commit()

    async def _ensure_active(
        self,
        *,
        inbound: TwilioInboundSms,
        scope: AgentScope,
        reason: str,
    ) -> None:
        remember_scope(user_phone_e164=inbound.from_e164, scope=scope)
        adapter = SmsGatewayAdapter(
            api=self._api,
            from_number=self._from_number,
            to_number=inbound.from_e164,
        )
        await turn_channel_up(
            scope,
            ChannelKind.SMS,
            adapter=adapter,
            reason=reason,
        )
        await ensure_presence(scope)
