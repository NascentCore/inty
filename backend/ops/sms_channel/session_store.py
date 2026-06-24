"""SMS gateway session store: in-memory presences + endpoint restore."""

from __future__ import annotations

from loguru import logger

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import ChannelKind
from app.db.session import AsyncSessionLocal
from app.external_services.twilio_sms import TwilioSmsApi
from app.services.agentic_channel.channel_runtime import turn_channel_up
from app.services.agentic_channel.companion_bonds import (
    get_companion_bond_for_scope,
    has_active_companion_bond,
    require_active_companion_bond,
)
from app.services.agentic_channel.endpoints import (
    EndpointRecord,
    list_endpoints_for_channel,
)
from app.services.agentic_channel.gateways.sms.adapter import SmsGatewayAdapter
from app.services.agentic_channel.presence import (
    clear_presences_for_tests,
    ensure_presence,
)

_scopes_by_user_phone: dict[str, AgentScope] = {}


def _phone_key(user_phone_e164: str) -> str:
    assert user_phone_e164 != ""
    return user_phone_e164


def remember_scope(*, user_phone_e164: str, scope: AgentScope) -> None:
    _scopes_by_user_phone[_phone_key(user_phone_e164)] = scope


def forget_scope(*, user_phone_e164: str) -> None:
    _scopes_by_user_phone.pop(_phone_key(user_phone_e164), None)


def clear_all_for_tests() -> None:
    _scopes_by_user_phone.clear()
    clear_presences_for_tests()


async def activate_sms_scope(
    *,
    record: EndpointRecord,
    api: TwilioSmsApi,
    from_number: str,
    reason: str,
) -> None:
    """Turn up SMS gateway, ensure presence, cache scope by user phone."""
    scope = record.to_scope()
    async with AsyncSessionLocal() as db:
        await require_active_companion_bond(db, scope)
    remember_scope(user_phone_e164=record.channel_address, scope=scope)
    adapter = SmsGatewayAdapter(
        api=api,
        from_number=from_number,
        to_number=record.channel_address,
    )
    await turn_channel_up(
        scope,
        ChannelKind.SMS,
        adapter=adapter,
        reason=reason,
    )
    await ensure_presence(scope)


async def restore_persisted_bindings(
    *,
    api: TwilioSmsApi,
    from_number: str,
) -> None:
    """Reload SMS endpoints with ACTIVE companion bonds and restart presences."""
    assert api is not None
    assert from_number != ""
    records = await list_endpoints_for_channel(channel=ChannelKind.SMS)
    restored_count = 0
    skipped_inactive = 0
    for record in records:
        scope = record.to_scope()
        try:
            async with AsyncSessionLocal() as db:
                bond_active = await has_active_companion_bond(db, scope)
                bond = (
                    await get_companion_bond_for_scope(db, scope)
                    if bond_active
                    else None
                )
            if not bond_active:
                skipped_inactive += 1
                continue
            if bond is not None and bond.runtime_paused_at is not None:
                skipped_inactive += 1
                continue
            await activate_sms_scope(
                record=record,
                api=api,
                from_number=from_number,
                reason="restore",
            )
            restored_count += 1
        except Exception:
            logger.exception(
                "sms-channel restore failed channel_address={}",
                record.channel_address,
            )
    if records:
        logger.info(
            "sms-channel: restored {} endpoint(s) skipped_inactive={} total={}",
            restored_count,
            skipped_inactive,
            len(records),
        )
