"""In-process agent-channel presence: shared inner-tick + tool_bg per scope."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.models import CompanionTurnResult
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.scope_turn_lock import get_scope_turn_lock
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.core.companion_harness.companion.utc import (
    strip_leading_transcript_timestamp_prefixes,
)
from app.core.config import global_config_loaded_from_config_yaml
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.schemas.chat import ChatCompletionRequest, ChatMessage
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.services import agent_service
from app.services.agentic_channel.channel_runtime import (
    get_scope_channel_registry,
)
from app.services.agentic_channel.turn import run_agent_turn
from app.services.agentic_companion.downlink import (
    DownlinkKind,
    downlink_delivers_user_visible_text,
    tool_background_downlink,
)
from app.services.agentic_companion.inner_tick_delivery import (
    inner_tick_delivery_for_telegram,
)
from app.services.agentic_companion.inner_tick_poll import run_inner_tick_poll
from app.services.agentic_companion.session import Coordinator, Session
from app.services.chat_service import generate_session_id
from app.services.agentic_channel.provision import resolve_chat_model_for_scope

_presences: dict[str, AgentChannelPresence] = {}
_presence_start_locks: dict[str, asyncio.Lock] = {}


def get_presence(scope: AgentScope) -> AgentChannelPresence | None:
    return _presences.get(scope.registry_key())


def clear_presences_for_tests() -> None:
    _presences.clear()
    _presence_start_locks.clear()


class AgentChannelPresence:
    """One scope: coordinator + inner-tick; downlink via ACTIVE channel registry."""

    def __init__(self, scope: AgentScope) -> None:
        assert scope is not None
        self._scope = scope
        self._loop = asyncio.get_running_loop()
        self._coordinator = Coordinator.for_loop(self._loop)
        self._session: Session | None = None
        self._tool_bg_task: asyncio.Task[None] | None = None

    @property
    def scope(self) -> AgentScope:
        return self._scope

    async def start(self) -> None:
        if self._session is not None:
            return
        synthetic_chat_id = self._scope.memory_store_chat_id()
        self._coordinator.store_inner_tick_coords(
            user_id=self._scope.user_id,
            agent_id=self._scope.agent_id,
            chat_id=synthetic_chat_id,
        )
        downlink = _ActiveChannelDownlink(self._scope)
        self._session = Session.from_coordinator(
            downlink=downlink,
            coordinator=self._coordinator,
        )
        poll_secs = float(
            global_config_loaded_from_config_yaml.app.features.companion_ws_proactive_chat_poll_seconds
        )
        delivery = inner_tick_delivery_for_telegram(
            self.send_assistant_text,
        )

        async def _run_poll(_ctx: dict) -> None:
            await run_inner_tick_poll(
                delivery=delivery,
                coordinator=self._coordinator,
                ws_conn_id=None,
                tc_box=None,
            )

        await self._session.start_inner_tick_worker(
            poll_seconds=poll_secs,
            run_one_poll=_run_poll,
        )
        self._tool_bg_task = asyncio.create_task(
            self._tool_background_consumer(),
            name=f"agent_channel_tool_bg_{self._scope.agent_id}",
        )

    async def stop(self) -> None:
        task = self._tool_bg_task
        if task is not None and (not task.done()):
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self._tool_bg_task = None
        if self._session is not None:
            await self._session.stop()
            self._session = None
        self._coordinator.sign_out()

    async def send_assistant_text(self, text: str) -> None:
        registry = get_scope_channel_registry(self._scope)
        active = registry.active_channel()
        if active is None:
            logger.warning(
                "agent_channel proactive drop: no ACTIVE channel scope={}",
                self._scope.registry_key(),
            )
            return
        downlink = registry.downlinks.get(active)
        if downlink is None:
            return
        from app.services.agentic_companion.downlink import Downlink

        await downlink.deliver(
            Downlink(
                kind=DownlinkKind.PROACTIVE,
                assistant_text=text,
                turn=None,
                tool_output=None,
                bootstrap_interim=None,
                scheduled_task_id=None,
                transcript_user_text=None,
            )
        )

    # TODO(channel-inbound-envelope): Accept reply-to + reaction fields; map channel message
    # IDs ↔ transcript UUIDs — epic #3440; Telegram #3441; Weixin #3442
    async def handle_user_text(
        self,
        user_text: str,
        *,
        runtime_channel: CompanionRuntimeChannel,
    ) -> str:
        stripped = user_text.strip()
        assert stripped
        preset_uid = str(uuid.uuid4())
        try:
            async with AsyncSessionLocal() as db:
                inty_user_row = await db.execute(
                    select(User).where(User.id == self._scope.user_id)
                )
                inty_user = inty_user_row.scalar_one_or_none()
                if inty_user is None:
                    return "无法找到你的 Inty 用户，请重新 /start。"
                agent_data = await agent_service.get_agent_for_chat(
                    db, self._scope.agent_id
                )
                if agent_data is None:
                    return "找不到这个 companion，请确认 agent_id 是否正确。"

            model = await resolve_chat_model_for_scope(self._scope)
            synthetic_chat_id = self._scope.memory_store_chat_id()
            session_id = generate_session_id(synthetic_chat_id)
            stub_request = ChatCompletionRequest(
                messages=[ChatMessage(role="user", content=stripped)],
                message_id=preset_uid,
            )
            self._coordinator.set_foreground_pending(
                preset_uid,
                {
                    "session_id": session_id,
                    "agent_id": self._scope.agent_id,
                    "user_id": self._scope.user_id,
                    "chat_id": synthetic_chat_id,
                    "request": stub_request,
                    "effective_local_id": None,
                },
            )
            # TODO(#3411): Telegram Bot API has no device timezone; manual E2E smoke:
            # inference → update_user_md → USER.md → LangSmith foreground ## User's Local Time Context.
            implicit_bundle = ImplicitSignalBundle(
                client_time=None,
                user_signed_on=False,
                server_received_at_utc=datetime.now(timezone.utc),
            )
            turn = await run_agent_turn(
                scope=self._scope,
                user_text=stripped,
                resolved_chat_model=model,
                runtime_channel=runtime_channel,
                background_output_sink=self._coordinator.background_sink,
                preset_user_msg_uuid=preset_uid,
                implicit_signal_bundle=implicit_bundle,
            )
            assert isinstance(turn, CompanionTurnResult)
            if not turn.tool_background_started:
                self._coordinator.remove_foreground_pending(preset_uid)
            reply = strip_leading_transcript_timestamp_prefixes(
                turn.assistant_text.strip()
            )
            if reply:
                return reply
            if turn.tool_background_started:
                # Tool output is delivered by _tool_background_consumer via downlink.
                return ""
            return "（没有回复内容）"
        except Exception:
            logger.exception(
                "agent_channel user_chat failed scope={}",
                self._scope.registry_key(),
            )
            self._coordinator.remove_foreground_pending(preset_uid)
            return "Companion 回合失败，请查看 Ops 日志。"

    async def _tool_background_consumer(self) -> None:
        while True:
            ev = await self._coordinator.background_events.get()
            ctx = self._coordinator.pop_foreground_pending(ev.user_msg_uuid)
            if ctx is None:
                logger.warning(
                    "agent_channel tool_bg missing foreground ctx user_msg_uuid={}",
                    ev.user_msg_uuid,
                )
                continue
            self._coordinator.set_foreground_pending(ev.user_msg_uuid, ctx)
            registry = get_scope_channel_registry(self._scope)
            active = registry.active_channel()
            if active is None:
                continue
            downlink = registry.downlinks.get(active)
            if downlink is None:
                continue
            try:
                scope_lock = get_scope_turn_lock(
                    CompanionScope(
                        user_id=self._scope.user_id,
                        companion_id=self._scope.agent_id,
                        chat_id=self._scope.memory_store_chat_id(),
                    )
                )
                async with scope_lock:
                    await downlink.deliver(
                        tool_background_downlink(tool_output=ev)
                    )
            except Exception:
                logger.exception("agent_channel tool_bg deliver failed")


class _ActiveChannelDownlink:
    """Routes Session downlink events to the ACTIVE channel adapter."""

    def __init__(self, scope: AgentScope) -> None:
        self._scope = scope

    async def deliver(self, event) -> None:
        if event.kind not in {
            DownlinkKind.USER_REPLY,
            DownlinkKind.PROACTIVE,
            DownlinkKind.SCHEDULED,
            DownlinkKind.MAINTENANCE,
        }:
            return
        if not downlink_delivers_user_visible_text(event):
            return
        registry = get_scope_channel_registry(self._scope)
        active = registry.active_channel()
        if active is None:
            return
        downlink = registry.downlinks.get(active)
        if downlink is None:
            return
        await downlink.deliver(event)


async def ensure_presence(scope: AgentScope) -> AgentChannelPresence:
    """Get or create and start presence for ``scope``."""
    key = scope.registry_key()
    existing = _presences.get(key)
    if existing is not None:
        return existing
    lock = _presence_start_locks.setdefault(key, asyncio.Lock())
    async with lock:
        existing = _presences.get(key)
        if existing is not None:
            return existing
        presence = AgentChannelPresence(scope)
        await presence.start()
        _presences[key] = presence
        return presence


async def stop_presence(scope: AgentScope) -> None:
    key = scope.registry_key()
    presence = _presences.pop(key, None)
    if presence is not None:
        await presence.stop()


async def stop_all_presences() -> None:
    keys = list(_presences.keys())
    for key in keys:
        presence = _presences.pop(key, None)
        if presence is not None:
            await presence.stop()
