"""In-process companion presence for Weixin demo bridge (no ``/api/v1/chat/ws`` loopback)."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from loguru import logger

from app.api import deps
from app.core.config import global_config_loaded_from_config_yaml
from app.core.model_selection import select_chat_model
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.schemas.chat import ChatCompletionRequest, ChatMessage
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.services import chat_service, companion_chat_service
from app.services.chat_service import generate_session_id
from app.services.agentic_companion.downlink import tool_background_downlink
from app.services.agentic_companion.inner_tick_delivery import (
    inner_tick_delivery_for_weixin,
)
from app.services.agentic_companion.inner_tick_poll import (
    run_inner_tick_poll,
)
from app.services.agentic_companion.session import (
    Coordinator,
    Session,
)
from app.services.global_services import subscription_service
from backend.ops.weixin_channel.session import WeixinChannelBinding
from backend.ops.weixin_channel.weixin_downlink import WeixinDownlink

if TYPE_CHECKING:
    from backend.ops.weixin_channel.transport import WeixinTransport


async def _inty_user_from_binding(binding: WeixinChannelBinding) -> User | None:
    """JWT ``sub`` is the Inty user; ``binding.user_id`` is only the demo session UUID."""
    async with AsyncSessionLocal() as db:
        return await deps.get_user_from_token(binding.inty_jwt, db)


class WeixinInprocessPresence:
    """One Weixin binding: companion coordinator + Hermes text downlink."""

    def __init__(self, binding: WeixinChannelBinding) -> None:
        assert binding is not None
        self._binding = binding
        self._loop = asyncio.get_running_loop()
        self._coordinator = Coordinator.for_loop(self._loop)
        self._downlink: WeixinDownlink | None = None
        self._presence: Session | None = None
        self._tool_bg_task: asyncio.Task[None] | None = None
        self._subscription_svc = subscription_service
        self._inty_user_id: str | None = None

    async def start(self, transport: WeixinTransport) -> None:
        """Resolve chat row, store inner-tick coords, start poll + tool_bg consumer."""
        assert transport is not None
        inty_user = await _inty_user_from_binding(self._binding)
        if inty_user is None:
            raise RuntimeError(
                "weixin inprocess presence: invalid or expired inty_jwt for demo bridge"
            )
        self._inty_user_id = str(inty_user.id)
        agent_id = self._binding.agent_id
        async with AsyncSessionLocal() as db:
            chat = await chat_service.get_or_create_chat_by_agent(
                db=db,
                user_id=self._inty_user_id,
                agent_id=agent_id,
            )
            await db.commit()
            chat_id = chat.id

        self._coordinator.store_inner_tick_coords(
            user_id=self._inty_user_id,
            agent_id=agent_id,
            chat_id=chat_id,
        )
        self._downlink = WeixinDownlink(
            transport,
            lambda: self._binding.last_peer_id,
        )
        self._presence = Session.from_coordinator(
            downlink=self._downlink,
            coordinator=self._coordinator,
        )
        poll_secs = float(
            global_config_loaded_from_config_yaml.app.features.companion_ws_proactive_chat_poll_seconds
        )
        delivery = inner_tick_delivery_for_weixin(
            self._push_weixin_assistant_text
        )

        async def _run_poll(ctx: dict) -> None:
            await run_inner_tick_poll(
                ctx=ctx,
                delivery=delivery,
                subscription_svc=self._subscription_svc,
                coordinator=self._coordinator,
                ws_conn_id=None,
                tc_box=None,
            )

        await self._presence.start_inner_tick_worker(
            poll_seconds=poll_secs,
            run_one_poll=_run_poll,
        )
        self._tool_bg_task = asyncio.create_task(
            self._tool_background_consumer(),
            name=f"weixin_tool_bg_{agent_id}",
        )

    async def stop(self) -> None:
        task = self._tool_bg_task
        if task is not None and (not task.done()):
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self._tool_bg_task = None
        if self._presence is not None:
            await self._presence.stop()
        self._coordinator.sign_out()
        self._inty_user_id = None

    async def handle_user_text(self, user_text: str) -> str:
        """Run one foreground user-chat turn; return assistant plain text for Hermes."""
        stripped = user_text.strip()
        assert stripped
        if self._inty_user_id is None:
            inty_user = await _inty_user_from_binding(self._binding)
            if inty_user is None:
                return (
                    "This demo bridge could not verify your Inty token. "
                    "Stop the session and start again with a valid JWT."
                )
            self._inty_user_id = str(inty_user.id)

        user_id = self._inty_user_id
        agent_id = self._binding.agent_id
        try:
            async with AsyncSessionLocal() as db:
                inty_user = await deps.get_user_from_token(
                    self._binding.inty_jwt, db
                )
                if inty_user is None:
                    return (
                        "This demo bridge could not verify your Inty token. "
                        "Stop the session and start again with a valid JWT."
                    )
                subscription = (
                    await self._subscription_svc.get_user_current_subscription(
                        db, user_id
                    )
                )
                model_override = select_chat_model(
                    user=inty_user,
                    is_subscribed=bool(subscription),
                )
                chat = await chat_service.get_or_create_chat_by_agent(
                    db=db,
                    user_id=user_id,
                    agent_id=agent_id,
                )
                await db.commit()
                chat_id = chat.id

            session_id = generate_session_id(str(chat_id))
            preset_uid = str(uuid.uuid4())
            stub_request = ChatCompletionRequest(
                messages=[ChatMessage(role="user", content=stripped)],
                message_id=preset_uid,
            )
            self._coordinator.set_foreground_pending(
                preset_uid,
                {
                    "session_id": session_id,
                    "agent_id": agent_id,
                    "request": stub_request,
                    "effective_local_id": None,
                    "user_id": user_id,
                },
            )
            implicit_bundle = ImplicitSignalBundle(
                client_time=None,
                user_signed_on=False,
                server_received_at_utc=datetime.now(timezone.utc),
            )
            async with self._coordinator.turn_lock:
                turn = await companion_chat_service.run_user_chat(
                    user_id=user_id,
                    agent_id=agent_id,
                    chat_id=chat_id,
                    user_text=stripped,
                    resolved_chat_model=model_override,
                    session_id=session_id,
                    background_output_sink=self._coordinator.background_sink,
                    preset_user_msg_uuid=preset_uid,
                    implicit_signal_bundle=implicit_bundle,
                )
            if not turn.tool_background_started:
                self._coordinator.remove_foreground_pending(preset_uid)
            reply = turn.assistant_text.strip()
            if reply:
                return reply
            if turn.tool_background_started:
                return "…"
            return "（没有回复内容）"
        except Exception:
            logger.exception(
                "weixin inprocess user_chat failed user_id={} agent_id={}",
                user_id,
                agent_id,
            )
            return "Companion turn failed. Check Ops logs for weixin inprocess user_chat."

    async def _push_weixin_assistant_text(self, text: str) -> None:
        assert self._downlink is not None
        await self._downlink.send_assistant_text(text)

    async def _tool_background_consumer(self) -> None:
        assert self._downlink is not None
        while True:
            ev = await self._coordinator.background_events.get()
            # Pop to detect stale uuid; re-set so deliver holds turn_lock without losing ctx.
            ctx = self._coordinator.pop_foreground_pending(ev.user_msg_uuid)
            if ctx is None:
                logger.warning(
                    "weixin tool_bg missing foreground ctx user_msg_uuid={}",
                    ev.user_msg_uuid,
                )
                continue
            self._coordinator.set_foreground_pending(ev.user_msg_uuid, ctx)
            try:
                async with self._coordinator.turn_lock:
                    await self._downlink.deliver(
                        tool_background_downlink(tool_output=ev)
                    )
            except Exception:
                logger.exception("weixin tool_bg deliver failed")
