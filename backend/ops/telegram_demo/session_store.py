"""Telegram demo session store: in-memory presences + agent_channel endpoint restore."""

from __future__ import annotations

from loguru import logger

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.db.session import AsyncSessionLocal
from app.external_services.telegram_bot_api import TelegramBotApi
from app.services.agentic_channel.adapters.telegram import (
    TelegramChannelAdapter,
)
from app.services.agentic_channel.channel_runtime import turn_channel_up
from app.services.agentic_channel.companion_bonds import (
    get_companion_bond_for_scope,
    has_active_companion_bond,
)
from app.services.agentic_channel.endpoints import (
    EndpointRecord,
    list_endpoints_for_channel,
)
from app.services.agentic_channel.presence import (
    clear_presences_for_tests,
    ensure_presence,
)

_scopes_by_address: dict[str, AgentScope] = {}


def _address_key(channel_address: str) -> str:
    assert channel_address != ""
    return channel_address


def get_scope_for_telegram_address(channel_address: str) -> AgentScope | None:
    return _scopes_by_address.get(_address_key(channel_address))


def remember_scope(
    *,
    channel_address: str,
    scope: AgentScope,
) -> None:
    _scopes_by_address[_address_key(channel_address)] = scope


def clear_all_for_tests() -> None:
    _scopes_by_address.clear()
    clear_presences_for_tests()


async def activate_telegram_scope(
    *,
    record: EndpointRecord,
    api: TelegramBotApi,
    reason: str,
) -> None:
    """Turn up Telegram channel, ensure presence, cache scope by address.

    TODO(telegram-launch-onboard-bond-gate): Require ACTIVE bond before ``ensure_presence``
    on onboard paths (restore already checks via caller) — #3533 (epic #3531).
    """
    scope = record.to_scope()
    remember_scope(channel_address=record.channel_address, scope=scope)
    adapter = TelegramChannelAdapter(
        api=api,
        channel_address=record.channel_address,
    )
    await turn_channel_up(
        scope,
        CompanionRuntimeChannel.TELEGRAM,
        adapter=adapter,
        reason=reason,
    )
    await ensure_presence(scope)


async def restore_persisted_bindings(*, api: TelegramBotApi) -> None:
    """Reload Telegram endpoints with ACTIVE companion bonds and restart presences."""
    assert api is not None
    records = await list_endpoints_for_channel(
        channel=CompanionRuntimeChannel.TELEGRAM
    )
    restored_count = 0
    skipped_inactive = 0
    for record in records:
        scope = record.to_scope()
        try:
            # TODO(!3491): Move ACTIVE-bond restore filtering into a shared
            # agent_channel restore service used by Telegram, Weixin, and future channels.
            async with AsyncSessionLocal() as db:
                bond_active = await has_active_companion_bond(db, scope)
                bond = (
                    await get_companion_bond_for_scope(db, scope)
                    if bond_active
                    else None
                )
            if not bond_active:
                skipped_inactive += 1
                logger.info(
                    "telegram-demo restore skipped inactive bond channel_address={} user_id={} agent_id={}",
                    record.channel_address,
                    scope.user_id,
                    scope.agent_id,
                )
                continue
            if bond is not None and bond.runtime_paused_at is not None:
                skipped_inactive += 1
                logger.info(
                    "telegram-demo restore skipped paused runtime channel_address={} user_id={} agent_id={}",
                    record.channel_address,
                    scope.user_id,
                    scope.agent_id,
                )
                continue
            await activate_telegram_scope(
                record=record,
                api=api,
                reason="restore",
            )
            restored_count += 1
        except Exception:
            logger.exception(
                "telegram-demo restore failed channel_address={}",
                record.channel_address,
            )
    if records:
        logger.info(
            "telegram-demo: restored {} agent_channel endpoint(s) skipped_inactive={} total={}",
            restored_count,
            skipped_inactive,
            len(records),
        )
