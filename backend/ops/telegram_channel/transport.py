"""Telegram Bot API long-poll transport for Ops Telegram channel.

TODO(telegram-channel-text-only): Non-text inbound (photo, voice, sticker) is ignored — #3349
TODO(telegram-shared-bot): Option A shared-bot routing — #3396
TODO(telegram-dedicated-bot-bonding): Option B per-user bot token + 1:1:1 user/bot/agent — #3361 (epic #3395)
TODO(telegram-reply-reaction-inbound): Route reply_to + emoji reaction updates into channel
  inbound envelope (not flat text only) — #3441 (epic #3440)
TODO(!3501): Optional transport-level text coalescing (Hermes ``_flush_text_batch``); prefer
  ``ScopeQueueServing`` post-drain quiet window for durable InputQueue semantics.
"""

from __future__ import annotations

import asyncio
from enum import StrEnum
from urllib.error import HTTPError

from loguru import logger

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)
from app.external_services.telegram_bot_api import (
    TelegramBotApi,
    TelegramIncomingMessage,
    TelegramParseMode,
)
from app.db.session import AsyncSessionLocal
from app.services.agentic_channel.adapters.telegram import (
    TelegramChannelAdapter,
)
from app.services.agentic_channel.channel_runtime import (
    turn_channel_up,
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
from app.services.agentic_channel.presence import ensure_presence, get_presence
from app.services.agentic_channel.companion_bonds import (
    get_companion_bond_for_scope,
    require_active_companion_bond,
    resume_companion_bond_runtime,
)
from app.services.agentic_channel.provision import (
    ChannelProvisionResult,
    provision_agent_for_channel_onboard,
    record_guest_campaign_attribution,
)
from backend.ops.telegram_channel.binding import (
    StartPayload,
    StartPayloadKind,
    parse_start_payload,
)
from backend.ops.telegram_channel.persistence import (
    load_poll_offset,
    save_poll_offset,
)
from backend.ops.telegram_channel.session_store import (
    activate_telegram_scope,
    remember_scope,
)

_ONBOARD_NOTICE_NEW = "Your agent is waking up and will greet you soon."
_ONBOARD_NOTICE_RETURNING = (
    "Welcome back. Your companion is ready — send a message anytime."
)
_ONBOARD_HINT = (
    "Open /telegram to scan the QR code, "
    "or send /start onboard here to connect."
)
_IDENTITY_MISMATCH = (
    "This Telegram account does not match our records. "
    "Please use the same account you used when connecting."
)
_BOND_UNAVAILABLE = (
    "We couldn't reconnect your companion. "
    "Please try again later or contact support."
)


class OnboardBondGatePath(StrEnum):
    """Structured-log path label for onboard bond gate rejections."""

    EXISTING_ENDPOINT = "existing_endpoint"
    PROVISION_RETURNING = "provision_returning"
    ACTIVATE_PROVISION = "activate_provision"
    PROVISION_CALL = "provision_call"


def _format_transport_notice(body: str) -> str:
    """Wrap platform copy in HTML italic for Telegram parse_mode=HTML."""
    assert body != ""
    return f"<i>{body}</i>"


def _log_poll_http_error(exc: HTTPError) -> None:
    """Log ``getUpdates`` HTTP failure; 409 is shared-bot long-poll contention."""
    match exc.code:
        case 409:
            logger.warning(
                "telegram-channel getUpdates HTTP 409 Conflict: another process is already "
                "long-polling this bot token (Telegram allows only one getUpdates client); "
                "stop other Ops instances, regression runs, or teammate machines using the "
                "same agent.channels.telegram.bot_token, or use a dedicated bot_token in "
                "config.yaml.local"
            )
        case _:
            logger.warning(
                "telegram-channel getUpdates HTTP {} {}: poll iteration failed; retrying",
                exc.code,
                exc.reason,
            )


class TelegramTransport:
    """Shared-bot ``getUpdates`` loop routing DMs via ``agent_channel_endpoints``."""

    def __init__(self, *, api: TelegramBotApi) -> None:
        assert api is not None
        self._api = api
        self._offset: int | None = None
        self._stop = asyncio.Event()
        self._long_poll_timeout_seconds = 30
        self._offset_loaded = False

    async def _ensure_offset_loaded(self) -> None:
        if self._offset_loaded:
            return
        self._offset = await load_poll_offset()
        self._offset_loaded = True

    async def run_until_stopped(self) -> None:
        await self._ensure_offset_loaded()
        while not self._stop.is_set():
            try:
                messages, next_offset = await asyncio.to_thread(
                    self._api.get_text_messages,
                    offset=self._offset,
                    timeout_seconds=self._long_poll_timeout_seconds,
                )
                if next_offset is not None:
                    self._offset = next_offset
                    await save_poll_offset(next_offset)
                for inbound in messages:
                    await self._handle_inbound(inbound)
            except asyncio.CancelledError:
                raise
            except HTTPError as exc:
                _log_poll_http_error(exc)
                await asyncio.sleep(2.0)
            except Exception:
                logger.exception(
                    "telegram-channel poll iteration failed: unexpected error"
                )
                await asyncio.sleep(2.0)

    async def stop(self) -> None:
        self._stop.set()

    async def _send_channel_text(
        self,
        *,
        chat_id: str,
        text: str,
    ) -> None:
        """Send one Telegram transport notice; not companion output, not OutputQueue."""
        assert chat_id != ""
        assert text != ""
        await asyncio.to_thread(
            self._api.send_message,
            chat_id=chat_id,
            text=_format_transport_notice(text),
            parse_mode=TelegramParseMode.HTML,
        )

    async def _handle_inbound(self, inbound: TelegramIncomingMessage) -> None:
        start = parse_start_payload(inbound.text)
        if start.kind == StartPayloadKind.ONBOARD:
            await self._handle_onboard(inbound=inbound, start=start)
            return
        scope = await resolve_scope(
            channel=ChannelKind.TELEGRAM,
            channel_address=inbound.chat_id,
        )
        if scope is None:
            await self._send_channel_text(
                chat_id=inbound.chat_id,
                text=_ONBOARD_HINT,
            )
            return
        try:
            await assert_inbound_endpoint_identity(
                channel=ChannelKind.TELEGRAM,
                channel_address=inbound.chat_id,
                channel_user_id=inbound.channel_user_id,
            )
        except ChannelEndpointConflictError:
            logger.warning(
                "telegram inbound channel_user_id mismatch chat_id={} from_id={}",
                inbound.chat_id,
                inbound.channel_user_id,
            )
            await self._send_channel_text(
                chat_id=inbound.chat_id,
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
            inbound.text,
            runtime_channel=ChannelKind.TELEGRAM,
        )
        if channel_error:
            await self._send_channel_text(
                chat_id=inbound.chat_id,
                text=channel_error,
            )

    async def _handle_onboard(
        self, *, inbound: TelegramIncomingMessage, start: StartPayload
    ) -> None:
        existing = await resolve_scope(
            channel=ChannelKind.TELEGRAM,
            channel_address=inbound.chat_id,
        )
        if existing is not None:
            try:
                await assert_inbound_endpoint_identity(
                    channel=ChannelKind.TELEGRAM,
                    channel_address=inbound.chat_id,
                    channel_user_id=inbound.channel_user_id,
                )
            except ChannelEndpointConflictError:
                logger.warning(
                    "telegram onboard identity mismatch chat_id={} from_id={}",
                    inbound.chat_id,
                    inbound.channel_user_id,
                )
                await self._send_channel_text(
                    chat_id=inbound.chat_id,
                    text=_IDENTITY_MISMATCH,
                )
                return
            if not await self._gate_onboard_bond(
                scope=existing,
                inbound=inbound,
                path=OnboardBondGatePath.EXISTING_ENDPOINT,
            ):
                return
            await self._resume_if_paused(scope=existing)
            await self._ensure_active(
                inbound=inbound,
                scope=existing,
                reason="onboard_returning",
            )
            logger.info(
                "telegram onboard returning chat_id={} from_id={} user_id={} agent_id={}",
                inbound.chat_id,
                inbound.channel_user_id,
                existing.user_id,
                existing.agent_id,
            )
            await self._send_channel_text(
                chat_id=inbound.chat_id,
                text=_ONBOARD_NOTICE_RETURNING,
            )
            return
        try:
            provision = await provision_agent_for_channel_onboard(
                channel=ChannelKind.TELEGRAM,
                channel_address=inbound.chat_id,
                channel_user_id=inbound.channel_user_id,
            )
        except CompanionBondInvariantError as exc:
            reject_scope = await resolve_scope(
                channel=ChannelKind.TELEGRAM,
                channel_address=inbound.chat_id,
            )
            await self._reject_onboard_for_bond(
                scope=reject_scope,
                inbound=inbound,
                path=OnboardBondGatePath.PROVISION_CALL,
                exc=exc,
            )
            return
        except (ValueError, ChannelEndpointConflictError) as exc:
            logger.warning(
                "telegram onboard failed chat_id={} from_id={} error={}",
                inbound.chat_id,
                inbound.channel_user_id,
                exc,
            )
            await self._send_channel_text(
                chat_id=inbound.chat_id,
                text=str(exc),
            )
            return
        if not provision.is_new_user:
            if not await self._gate_onboard_bond(
                scope=provision.scope,
                inbound=inbound,
                path=OnboardBondGatePath.PROVISION_RETURNING,
            ):
                return
            await self._resume_if_paused(scope=provision.scope)
            await self._ensure_active(
                inbound=inbound,
                scope=provision.scope,
                reason="onboard_returning",
            )
            logger.info(
                "telegram onboard returning after provision chat_id={} from_id={} user_id={} agent_id={}",
                inbound.chat_id,
                inbound.channel_user_id,
                provision.scope.user_id,
                provision.scope.agent_id,
            )
            await self._send_channel_text(
                chat_id=inbound.chat_id,
                text=_ONBOARD_NOTICE_RETURNING,
            )
            return
        logger.info(
            "telegram onboard new chat_id={} from_id={} user_id={} agent_id={}",
            inbound.chat_id,
            inbound.channel_user_id,
            provision.scope.user_id,
            provision.scope.agent_id,
        )
        if start.campaign is not None:
            await record_guest_campaign_attribution(
                user_id=provision.scope.user_id,
                campaign=start.campaign,
            )
        await self._activate_provision(
            inbound=inbound,
            provision=provision,
        )

    async def _activate_provision(
        self,
        *,
        inbound: TelegramIncomingMessage,
        provision: ChannelProvisionResult,
    ) -> None:
        if not await self._gate_onboard_bond(
            scope=provision.scope,
            inbound=inbound,
            path=OnboardBondGatePath.ACTIVATE_PROVISION,
        ):
            return
        record = EndpointRecord(
            user_id=provision.scope.user_id,
            agent_id=provision.scope.agent_id,
            channel=ChannelKind.TELEGRAM,
            channel_address=provision.channel_address,
            channel_user_id=provision.channel_user_id,
        )
        await activate_telegram_scope(
            record=record,
            api=self._api,
            reason="onboard",
        )
        presence = get_presence(provision.scope)
        if presence is None:
            presence = await ensure_presence(provision.scope)
        await self._send_channel_text(
            chat_id=inbound.chat_id,
            text=_ONBOARD_NOTICE_NEW,
        )
        try:
            await presence.greet_on_sign_on(
                runtime_channel=ChannelKind.TELEGRAM,
            )
        except Exception:
            logger.exception(
                "telegram onboard greeting failed chat_id={} user_id={} agent_id={}",
                inbound.chat_id,
                provision.scope.user_id,
                provision.scope.agent_id,
            )

    async def _reject_onboard_for_bond(
        self,
        *,
        scope: AgentScope | None,
        inbound: TelegramIncomingMessage,
        path: OnboardBondGatePath,
        exc: CompanionBondInvariantError,
    ) -> None:
        """Log bond rejection and send static onboard notice without starting runtime."""
        scope_key = scope.registry_key() if scope is not None else "unknown"
        logger.warning(
            "telegram_onboard_rejected_bond path={} scope={} chat_id={} from_id={} reason={}",
            path.value,
            scope_key,
            inbound.chat_id,
            inbound.channel_user_id,
            exc,
        )
        await self._send_channel_text(
            chat_id=inbound.chat_id,
            text=_BOND_UNAVAILABLE,
        )

    async def _gate_onboard_bond(
        self,
        *,
        scope: AgentScope,
        inbound: TelegramIncomingMessage,
        path: OnboardBondGatePath,
    ) -> bool:
        """Return whether scope has a runnable ACTIVE bond before onboard runtime start."""
        try:
            async with AsyncSessionLocal() as db:
                await require_active_companion_bond(db, scope)
        except CompanionBondInvariantError as exc:
            await self._reject_onboard_for_bond(
                scope=scope,
                inbound=inbound,
                path=path,
                exc=exc,
            )
            return False
        return True

    async def _resume_if_paused(self, *, scope: AgentScope) -> None:
        """Clear runtime pause flag before normal Telegram runtime activation."""
        async with AsyncSessionLocal() as db:
            bond = await get_companion_bond_for_scope(db, scope)
            if bond is None or bond.runtime_paused_at is None:
                return
            resumed = await resume_companion_bond_runtime(db, scope)
            if not resumed:
                return
            await db.commit()
        logger.info(
            "runtime_resume scope={} channel={}",
            scope.registry_key(),
            ChannelKind.TELEGRAM.value,
        )

    async def _ensure_active(
        self,
        *,
        inbound: TelegramIncomingMessage,
        scope,
        reason: str,
    ) -> None:
        remember_scope(channel_address=inbound.chat_id, scope=scope)
        adapter = TelegramChannelAdapter(
            api=self._api,
            channel_address=inbound.chat_id,
        )
        await turn_channel_up(
            scope,
            ChannelKind.TELEGRAM,
            adapter=adapter,
            reason=reason,
        )
        await ensure_presence(scope)
