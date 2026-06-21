"""Telegram Bot API long-poll transport for Ops telegram-demo.

TODO(telegram-demo-text-only): Non-text inbound (photo, voice, sticker) is ignored — #3349
TODO(telegram-shared-bot): Option A shared-bot routing — #3396
TODO(telegram-dedicated-bot-bonding): Option B per-user bot token + 1:1:1 user/bot/agent — #3361 (epic #3395)
TODO(telegram-reply-reaction-inbound): Route reply_to + emoji reaction updates into channel
  inbound envelope (not flat text only) — #3441 (epic #3440)
TODO(!3501): Optional transport-level text coalescing (Hermes ``_flush_text_batch``); prefer
  ``ScopeQueueServing`` post-drain quiet window for durable InputQueue semantics.
TODO(telegram-launch-onboard-bond-gate): Fail-closed ACTIVE ``companion_bonds`` check before
  ``activate_telegram_scope`` / ``ensure_presence``; catch ``CompanionBondInvariantError`` — #3533
  (epic #3531).
"""

from __future__ import annotations

import asyncio

from loguru import logger

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
)
from app.external_services.telegram_bot_api import (
    TelegramBotApi,
    TelegramIncomingMessage,
)
from app.db.session import AsyncSessionLocal
from app.services.agentic_channel.adapters.telegram import (
    TelegramChannelAdapter,
)
from app.services.agentic_channel.channel_runtime import (
    get_scope_channel_registry,
    turn_channel_up,
)
from app.services.agentic_channel.endpoints import (
    EndpointRecord,
    assert_inbound_endpoint_identity,
    resolve_scope,
)
from app.services.agentic_channel.errors import ChannelEndpointConflictError
from app.services.agentic_channel.presence import ensure_presence, get_presence
from app.services.agentic_channel.companion_bonds import (
    get_companion_bond_for_scope,
    resume_companion_bond_runtime,
)
from app.services.agentic_channel.provision import (
    ChannelProvisionResult,
    provision_agent_for_channel_onboard,
)
from app.services.agentic_companion.downlink import Downlink, DownlinkKind
from backend.ops.telegram_demo.binding import (
    StartPayloadKind,
    parse_start_payload,
)
from backend.ops.telegram_demo.persistence import (
    load_poll_offset,
    save_poll_offset,
)
from backend.ops.telegram_demo.session_store import (
    activate_telegram_scope,
    remember_scope,
)

_WELCOME_RETURNING = (
    "Welcome back! Your companion is ready. Just send a message."
)
_ONBOARD_HINT = (
    "Open /telegram to scan the QR code, "
    "or send /start onboard here to connect."
)
_IDENTITY_MISMATCH = (
    "This Telegram account does not match our records. "
    "Please use the same account you used when connecting."
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
            except Exception:
                logger.exception("telegram-demo poll iteration failed")
                await asyncio.sleep(2.0)

    async def stop(self) -> None:
        self._stop.set()

    async def _send_channel_text(
        self,
        *,
        chat_id: str,
        text: str,
        scope: AgentScope | None = None,
    ) -> None:
        """Send one Telegram control notice that is not companion output."""
        assert chat_id != ""
        assert text != ""
        if scope is not None:
            registry = get_scope_channel_registry(scope)
            downlink = registry.downlinks.get(ChannelKind.TELEGRAM)
            if downlink is not None:
                await downlink.deliver(
                    Downlink(
                        kind=DownlinkKind.USER_REPLY,
                        assistant_text=text,
                        turn=None,
                        tool_output=None,
                        bootstrap_interim=None,
                        scheduled_task_id=None,
                        transcript_user_text=None,
                    )
                )
                return
        adapter = TelegramChannelAdapter(
            api=self._api,
            channel_address=chat_id,
        )
        await adapter.as_downlink().deliver(
            Downlink(
                kind=DownlinkKind.USER_REPLY,
                assistant_text=text,
                turn=None,
                tool_output=None,
                bootstrap_interim=None,
                scheduled_task_id=None,
                transcript_user_text=None,
            )
        )

    async def _handle_inbound(self, inbound: TelegramIncomingMessage) -> None:
        start = parse_start_payload(inbound.text)
        if start.kind == StartPayloadKind.ONBOARD:
            await self._handle_onboard(inbound=inbound)
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
                scope=scope,
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
                scope=scope,
            )

    async def _handle_onboard(
        self, *, inbound: TelegramIncomingMessage
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
                    scope=existing,
                )
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
                text=_WELCOME_RETURNING,
                scope=existing,
            )
            return
        try:
            provision = await provision_agent_for_channel_onboard(
                channel=ChannelKind.TELEGRAM,
                channel_address=inbound.chat_id,
                channel_user_id=inbound.channel_user_id,
            )
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
                text=_WELCOME_RETURNING,
                scope=provision.scope,
            )
            return
        logger.info(
            "telegram onboard new chat_id={} from_id={} user_id={} agent_id={}",
            inbound.chat_id,
            inbound.channel_user_id,
            provision.scope.user_id,
            provision.scope.agent_id,
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
