"""Guest user + agent provisioning for agent-channel onboard (no legacy chat row).

Identity for companion / telegram-channel / weixin paths uses ``User.id`` and ``Agent.id``
only. Do **not** read or write legacy ``readable_id`` here (maintenance-mode HTTP APIs
may still touch it). Enforced by ``chat_ws_boundary.companion_surface_readable_id_references``.

TODO(telegram-dedicated-bot-bonding): Triage portal to provision per-user bot token and
  bind 1 user : 1 bot : 1 agent — #3361 (epic #3395; Option A constraints #3396)

TODO(shared-companion-provisioning): #3697 — route this onboard path through the
  shared provisioning service and canonical channel identity resolution (epic #3491).
"""

from __future__ import annotations

from dataclasses import dataclass

from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import flag_modified

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.external_services.telegram_bot import CampaignAttribution
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)
from app.core.model_selection import select_chat_model
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services.agentic_channel.companion_bonds import (
    ensure_active_companion_bond_for_owned_scope,
    require_active_companion_bond,
)
from app.services.agentic_channel.companion_guest_provision import (
    ProvisionGuestScopeInput,
    provision_guest_scope,
)
from app.services.agentic_channel.endpoints import (
    assert_inbound_endpoint_identity,
    resolve_scope,
    resolve_scope_by_channel_user_id,
    upsert_endpoint_in_session,
)
from app.services.agentic_channel.errors import (
    ChannelEndpointConflictError,
    integrity_error_detail,
)
from app.services.agentic_channel.session import ensure_memory_store_session
from app.services.user_profile_persistence import (
    seed_profile_collection_required_in_context,
)


def _guest_meta_data_for_channel(channel: ChannelKind) -> dict:
    """Guest user meta_data payload for agent-channel onboard."""
    base = {"agent_channel": True}
    match channel:
        case ChannelKind.TELEGRAM:
            return {**base, "profile_collection_required": True}
        case _:
            return base


from app.services.global_services import subscription_service


@dataclass(frozen=True)
class ChannelProvisionResult:
    scope: AgentScope
    is_new_user: bool
    channel_address: str
    channel_user_id: str


@dataclass(frozen=True)
class OwnedChannelProvisionInput:
    """Bundled inputs for owned-scope channel provision (caller-known user + agent)."""

    channel: ChannelKind
    channel_address: str
    channel_user_id: str
    scope: AgentScope


async def _require_active_bond_for_scope(scope: AgentScope) -> None:
    async with AsyncSessionLocal() as db:
        await require_active_companion_bond(db, scope)


async def _try_finish_existing_channel_provision(
    *,
    channel: ChannelKind,
    channel_address: str,
    channel_user_id: str,
    expected_scope: AgentScope | None,
) -> ChannelProvisionResult | None:
    """Return existing endpoint provision when resolved; None when no row exists."""
    by_address = await resolve_scope(
        channel=channel, channel_address=channel_address
    )
    by_user = await resolve_scope_by_channel_user_id(
        channel=channel, channel_user_id=channel_user_id
    )
    if by_address is None and by_user is None:
        return None
    if (
        expected_scope is not None
        and by_address is None
        and by_user is not None
        and by_user.user_id == expected_scope.user_id
        and by_user.registry_key() != expected_scope.registry_key()
    ):
        return None
    await assert_inbound_endpoint_identity(
        channel=channel,
        channel_address=channel_address,
        channel_user_id=channel_user_id,
    )
    if by_address is not None and by_user is not None:
        if by_address.registry_key() != by_user.registry_key():
            logger.warning(
                "agent_channel provision scope split channel={} channel_address={} channel_user_id={} by_address={} by_user={}",
                channel.value,
                channel_address,
                channel_user_id,
                by_address.registry_key(),
                by_user.registry_key(),
            )
            raise ChannelEndpointConflictError(
                "channel_address and channel_user_id resolve to different scopes"
            )
        resolved = by_address
    elif by_address is not None:
        resolved = by_address
    else:
        assert by_user is not None
        resolved = by_user
    if (
        expected_scope is not None
        and resolved.registry_key() != expected_scope.registry_key()
    ):
        raise ChannelEndpointConflictError(
            f"existing endpoint scope {resolved.registry_key()} "
            f"does not match {expected_scope.registry_key()}"
        )
    logger.info(
        "agent_channel provision existing scope channel={} channel_address={} channel_user_id={} user_id={} agent_id={}",
        channel.value,
        channel_address,
        channel_user_id,
        resolved.user_id,
        resolved.agent_id,
    )
    await _require_active_bond_for_scope(resolved)
    return ChannelProvisionResult(
        scope=resolved,
        is_new_user=False,
        channel_address=channel_address,
        channel_user_id=channel_user_id,
    )


async def _provision_result_after_bind_race(
    *,
    channel: ChannelKind,
    channel_address: str,
    channel_user_id: str,
) -> ChannelProvisionResult:
    """Return existing scope when a concurrent transaction won the endpoint insert."""
    raced = await resolve_scope(
        channel=channel, channel_address=channel_address
    )
    if raced is None:
        raced = await resolve_scope_by_channel_user_id(
            channel=channel, channel_user_id=channel_user_id
        )
    if raced is None:
        logger.error(
            "agent_channel onboard race recovery failed channel={} channel_address={} channel_user_id={}",
            channel.value,
            channel_address,
            channel_user_id,
        )
        raise ChannelEndpointConflictError(
            "endpoint bind violates unique constraint"
        )
    logger.info(
        "agent_channel onboard race recovery ok channel={} channel_address={} channel_user_id={} user_id={} agent_id={}",
        channel.value,
        channel_address,
        channel_user_id,
        raced.user_id,
        raced.agent_id,
    )
    await assert_inbound_endpoint_identity(
        channel=channel,
        channel_address=channel_address,
        channel_user_id=channel_user_id,
    )
    await _require_active_bond_for_scope(raced)
    await ensure_memory_store_session(raced)
    return ChannelProvisionResult(
        scope=raced,
        is_new_user=False,
        channel_address=channel_address,
        channel_user_id=channel_user_id,
    )


async def provision_agent_for_channel_onboard(
    *,
    channel: ChannelKind,
    channel_address: str,
    channel_user_id: str,
) -> ChannelProvisionResult:
    """Idempotent onboard: resolve existing endpoint or create guest user + agent."""
    assert channel_address != ""
    assert channel_user_id != ""

    existing = await _try_finish_existing_channel_provision(
        channel=channel,
        channel_address=channel_address,
        channel_user_id=channel_user_id,
        expected_scope=None,
    )
    if existing is not None:
        return existing

    async with AsyncSessionLocal() as db:
        pending_user_id = ""
        pending_agent_id = ""
        try:
            scope = await provision_guest_scope(
                db,
                ProvisionGuestScopeInput(
                    channel=channel,
                    nickname_prefix="Guest",
                    meta_data=_guest_meta_data_for_channel(channel),
                ),
            )
            pending_user_id = scope.user_id
            pending_agent_id = scope.agent_id
            await upsert_endpoint_in_session(
                db,
                scope,
                channel=channel,
                channel_address=channel_address,
                channel_user_id=channel_user_id,
            )
            await db.commit()
        except ChannelEndpointConflictError as exc:
            logger.warning(
                "agent_channel onboard bind conflict channel={} channel_address={} channel_user_id={} user_id={} agent_id={} error={}",
                channel.value,
                channel_address,
                channel_user_id,
                pending_user_id,
                pending_agent_id,
                exc,
            )
            await db.rollback()
            return await _provision_result_after_bind_race(
                channel=channel,
                channel_address=channel_address,
                channel_user_id=channel_user_id,
            )
        except IntegrityError as exc:
            logger.warning(
                "agent_channel onboard integrity error channel={} channel_address={} channel_user_id={} user_id={} agent_id={} {}",
                channel.value,
                channel_address,
                channel_user_id,
                pending_user_id,
                pending_agent_id,
                integrity_error_detail(exc),
            )
            await db.rollback()
            return await _provision_result_after_bind_race(
                channel=channel,
                channel_address=channel_address,
                channel_user_id=channel_user_id,
            )

    logger.info(
        "agent_channel onboard created channel={} channel_address={} channel_user_id={} user_id={} agent_id={}",
        channel.value,
        channel_address,
        channel_user_id,
        scope.user_id,
        scope.agent_id,
    )
    session = await ensure_memory_store_session(scope)
    if channel == ChannelKind.TELEGRAM:
        seed_profile_collection_required_in_context(
            session.store,
            required=True,
        )
    return ChannelProvisionResult(
        scope=scope,
        is_new_user=True,
        channel_address=channel_address,
        channel_user_id=channel_user_id,
    )


async def provision_owned_agent_for_channel(
    *,
    input: OwnedChannelProvisionInput,
) -> ChannelProvisionResult:
    """Provision owned user+agent scope: bond ensure, endpoint bind, MemoryStore."""
    assert input.channel_address != ""
    assert input.channel_user_id != ""
    channel = input.channel
    channel_address = input.channel_address
    channel_user_id = input.channel_user_id
    scope = input.scope

    existing = await _try_finish_existing_channel_provision(
        channel=channel,
        channel_address=channel_address,
        channel_user_id=channel_user_id,
        expected_scope=scope,
    )
    if existing is not None:
        return existing

    pending_user_id = scope.user_id
    pending_agent_id = scope.agent_id
    async with AsyncSessionLocal() as db:
        try:
            await ensure_active_companion_bond_for_owned_scope(db, scope)
            await upsert_endpoint_in_session(
                db,
                scope,
                channel=channel,
                channel_address=channel_address,
                channel_user_id=channel_user_id,
            )
            await db.commit()
        except ChannelEndpointConflictError as exc:
            logger.warning(
                "agent_channel owned provision bind conflict channel={} channel_address={} channel_user_id={} user_id={} agent_id={} error={}",
                channel.value,
                channel_address,
                channel_user_id,
                pending_user_id,
                pending_agent_id,
                exc,
            )
            await db.rollback()
            return await _provision_result_after_bind_race(
                channel=channel,
                channel_address=channel_address,
                channel_user_id=channel_user_id,
            )
        except IntegrityError as exc:
            logger.warning(
                "agent_channel owned provision integrity error channel={} channel_address={} channel_user_id={} user_id={} agent_id={} {}",
                channel.value,
                channel_address,
                channel_user_id,
                pending_user_id,
                pending_agent_id,
                integrity_error_detail(exc),
            )
            await db.rollback()
            return await _provision_result_after_bind_race(
                channel=channel,
                channel_address=channel_address,
                channel_user_id=channel_user_id,
            )

    logger.info(
        "agent_channel owned provision created channel={} channel_address={} channel_user_id={} user_id={} agent_id={}",
        channel.value,
        channel_address,
        channel_user_id,
        scope.user_id,
        scope.agent_id,
    )
    await ensure_memory_store_session(scope)
    return ChannelProvisionResult(
        scope=scope,
        is_new_user=False,
        channel_address=channel_address,
        channel_user_id=channel_user_id,
    )


async def record_guest_campaign_attribution(
    *,
    user_id: str,
    campaign: CampaignAttribution,
) -> None:
    """Persist first-touch Telegram campaign attribution onto a guest user.

    Localized, additive write invoked only on new-user onboard so the shared
    ``provision_agent_for_channel_onboard`` signature stays untouched. Writes
    under ``meta_data.campaign`` and is idempotent per first ``/start``.
    """
    assert user_id != ""
    assert campaign is not None
    async with AsyncSessionLocal() as db:
        user_row = await db.execute(select(User).where(User.id == user_id))
        user = user_row.scalar_one_or_none()
        if user is None:
            logger.warning(
                "campaign attribution skipped: user not found user_id={}",
                user_id,
            )
            return
        meta = dict(user.meta_data) if isinstance(user.meta_data, dict) else {}
        meta["campaign"] = {
            "source": campaign.source,
            "medium": campaign.medium,
            "campaign": campaign.campaign,
        }
        user.meta_data = meta
        flag_modified(user, "meta_data")
        await db.commit()
    logger.info(
        "campaign attribution recorded user_id={} source={} medium={} campaign={}",
        user_id,
        campaign.source,
        campaign.medium,
        campaign.campaign,
    )


async def resolve_chat_model_for_scope(scope: AgentScope):
    """Select chat model for a guest scope (subscription-aware)."""
    async with AsyncSessionLocal() as db:
        user_row = await db.execute(
            select(User).where(User.id == scope.user_id)
        )
        user = user_row.scalar_one_or_none()
        if user is None:
            raise ValueError(f"user not found: {scope.user_id}")
        subscription = await subscription_service.get_user_current_subscription(
            db, scope.user_id
        )
        return select_chat_model(
            user=user,
            is_subscribed=bool(subscription),
        )
