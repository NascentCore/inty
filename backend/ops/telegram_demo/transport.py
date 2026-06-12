"""Telegram Bot API long-poll transport for Ops telegram-demo.

TODO(telegram-demo-text-only): Non-text inbound (photo, voice, sticker) is ignored — #3349
"""

from __future__ import annotations

import asyncio

from loguru import logger

from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.external_services.telegram_bot_api import (
    TelegramBotApi,
    TelegramIncomingMessage,
)
from app.services.agentic_channel.adapters.telegram import (
    TelegramChannelAdapter,
)
from app.services.agentic_channel.channel_runtime import turn_channel_up
from app.services.agentic_channel.endpoints import (
    EndpointRecord,
    assert_inbound_endpoint_identity,
    resolve_scope,
)
from app.services.agentic_channel.errors import ChannelEndpointConflictError
from app.services.agentic_channel.presence import ensure_presence, get_presence
from app.services.agentic_channel.provision import (
    ChannelProvisionResult,
    provision_agent_for_channel_onboard,
)
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

_WELCOME_NEW = (
    "欢迎！已为你创建 companion，可以直接发中文消息。"
    "完成 bootstrap 后 companion 会更了解你。"
)
_WELCOME_RETURNING = "欢迎回来！已绑定 companion，可以直接发消息聊天。"
_ONBOARD_HINT = (
    "请先打开 Ops /telegram-demo 页面扫码，"
    "或在对话中发送 /start onboard 完成绑定。"
)
_IDENTITY_MISMATCH = (
    "Telegram 用户身份与绑定记录不符，无法处理消息。"
    "请确认使用同一 Telegram 账号。"
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
                    reply = await self._handle_inbound(inbound)
                    if reply:
                        await asyncio.to_thread(
                            self._api.send_message,
                            chat_id=inbound.chat_id,
                            text=reply,
                        )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("telegram-demo poll iteration failed")
                await asyncio.sleep(2.0)

    async def stop(self) -> None:
        self._stop.set()

    async def _handle_inbound(self, inbound: TelegramIncomingMessage) -> str:
        start = parse_start_payload(inbound.text)
        if start.kind == StartPayloadKind.ONBOARD:
            return await self._handle_onboard(inbound=inbound)
        scope = await resolve_scope(
            channel=CompanionRuntimeChannel.TELEGRAM,
            channel_address=inbound.chat_id,
        )
        if scope is None:
            return _ONBOARD_HINT
        try:
            await assert_inbound_endpoint_identity(
                channel=CompanionRuntimeChannel.TELEGRAM,
                channel_address=inbound.chat_id,
                channel_user_id=inbound.channel_user_id,
            )
        except ChannelEndpointConflictError:
            logger.warning(
                "telegram inbound channel_user_id mismatch chat_id={} from_id={}",
                inbound.chat_id,
                inbound.channel_user_id,
            )
            return _IDENTITY_MISMATCH
        await self._ensure_active(
            inbound=inbound,
            scope=scope,
            reason="inbound_message",
        )
        presence = get_presence(scope)
        if presence is None:
            presence = await ensure_presence(scope)
        return await presence.handle_user_text(
            inbound.text,
            runtime_channel=CompanionRuntimeChannel.TELEGRAM,
        )

    async def _handle_onboard(self, *, inbound: TelegramIncomingMessage) -> str:
        existing = await resolve_scope(
            channel=CompanionRuntimeChannel.TELEGRAM,
            channel_address=inbound.chat_id,
        )
        if existing is not None:
            try:
                await assert_inbound_endpoint_identity(
                    channel=CompanionRuntimeChannel.TELEGRAM,
                    channel_address=inbound.chat_id,
                    channel_user_id=inbound.channel_user_id,
                )
            except ChannelEndpointConflictError:
                logger.warning(
                    "telegram onboard identity mismatch chat_id={} from_id={}",
                    inbound.chat_id,
                    inbound.channel_user_id,
                )
                return _IDENTITY_MISMATCH
            await self._ensure_active(
                inbound=inbound,
                scope=existing,
                reason="onboard_returning",
            )
            return _WELCOME_RETURNING
        try:
            provision = await provision_agent_for_channel_onboard(
                channel=CompanionRuntimeChannel.TELEGRAM,
                channel_address=inbound.chat_id,
                channel_user_id=inbound.channel_user_id,
            )
        except (ValueError, ChannelEndpointConflictError) as exc:
            return str(exc)
        if not provision.is_new_user:
            await self._ensure_active(
                inbound=inbound,
                scope=provision.scope,
                reason="onboard_returning",
            )
            return _WELCOME_RETURNING
        return await self._activate_provision(
            inbound=inbound,
            provision=provision,
        )

    async def _activate_provision(
        self,
        *,
        inbound: TelegramIncomingMessage,
        provision: ChannelProvisionResult,
    ) -> str:
        record = EndpointRecord(
            user_id=provision.scope.user_id,
            agent_id=provision.scope.agent_id,
            channel=CompanionRuntimeChannel.TELEGRAM,
            channel_address=provision.channel_address,
            channel_user_id=provision.channel_user_id,
        )
        await activate_telegram_scope(
            record=record,
            api=self._api,
            reason="onboard",
        )
        return _WELCOME_NEW

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
            CompanionRuntimeChannel.TELEGRAM,
            adapter=adapter,
            reason=reason,
        )
        await ensure_presence(scope)
