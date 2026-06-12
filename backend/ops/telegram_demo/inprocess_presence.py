"""In-process companion presence for Telegram demo (inner-tick + tool_bg downlink)."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select

from app.core.config import global_config_loaded_from_config_yaml
from app.core.model_selection import select_chat_model
from app.db.session import AsyncSessionLocal
from app.external_services.telegram_bot_api import TelegramBotApi
from app.models.user import User
from app.schemas.chat import ChatCompletionRequest, ChatMessage
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.services import agent_service, chat_service, companion_chat_service
from app.services.chat_service import generate_session_id
from app.services.agentic_companion.downlink import tool_background_downlink
from app.services.agentic_companion.inner_tick_delivery import (
    inner_tick_delivery_for_telegram,
)
from app.services.agentic_companion.inner_tick_poll import run_inner_tick_poll
from app.services.agentic_companion.session import Coordinator, Session
from app.services.global_services import subscription_service
from backend.ops.telegram_demo.binding import TelegramDemoBinding
from backend.ops.telegram_demo.telegram_downlink import TelegramDownlink


class TelegramInprocessPresence:
    """One Telegram chat binding: companion coordinator + Telegram sendMessage pipe."""

    def __init__(self, binding: TelegramDemoBinding) -> None:
        assert binding is not None
        self._binding = binding
        self._loop = asyncio.get_running_loop()
        self._coordinator = Coordinator.for_loop(self._loop)
        self._downlink: TelegramDownlink | None = None
        self._presence: Session | None = None
        self._tool_bg_task: asyncio.Task[None] | None = None
        self._subscription_svc = subscription_service
        self._inty_user_id: str | None = None

    async def start(self, *, api: TelegramBotApi) -> None:
        """Store inner-tick coords, start poll worker, and tool_bg consumer."""
        assert api is not None
        if self._presence is not None:
            return
        user_id = self._binding.user_id
        agent_id = self._binding.agent_id
        async with AsyncSessionLocal() as db:
            chat = await chat_service.get_or_create_chat_by_agent(
                db=db,
                user_id=user_id,
                agent_id=agent_id,
            )
            await db.commit()
            chat_id = chat.id
        self._inty_user_id = user_id
        self._coordinator.store_inner_tick_coords(
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat_id,
        )
        chat_id_fixed = self._binding.telegram_chat_id
        self._downlink = TelegramDownlink(
            api=api,
            chat_id_resolver=lambda: chat_id_fixed,
        )
        self._presence = Session.from_coordinator(
            downlink=self._downlink,
            coordinator=self._coordinator,
        )
        poll_secs = float(
            global_config_loaded_from_config_yaml.app.features.companion_ws_proactive_chat_poll_seconds
        )
        delivery = inner_tick_delivery_for_telegram(
            self._push_telegram_assistant_text
        )

        async def _run_poll(_ctx: dict) -> None:
            await run_inner_tick_poll(
                delivery=delivery,
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
            name=f"telegram_tool_bg_{agent_id}",
        )

    async def stop(self) -> None:
        task = self._tool_bg_task
        if task is not None and (not task.done()):
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self._tool_bg_task = None
        if self._presence is not None:
            await self._presence.stop()
            self._presence = None
        self._downlink = None
        self._coordinator.sign_out()
        self._inty_user_id = None

    async def handle_user_text(self, user_text: str) -> str:
        """Run one user-chat turn; inline-await one tool_bg event when needed."""
        stripped = user_text.strip()
        assert stripped
        user_id = self._binding.user_id
        agent_id = self._binding.agent_id
        chat_id = self._binding.chat_id
        preset_uid = str(uuid.uuid4())
        try:
            async with AsyncSessionLocal() as db:
                inty_user_row = await db.execute(
                    select(User).where(User.id == user_id)
                )
                inty_user = inty_user_row.scalar_one_or_none()
                if inty_user is None:
                    return "无法找到你的 Inty 用户，请重新 /start。"
                subscription = (
                    await self._subscription_svc.get_user_current_subscription(
                        db, user_id
                    )
                )
                model_override = select_chat_model(
                    user=inty_user,
                    is_subscribed=bool(subscription),
                )
                agent_data = await agent_service.get_agent_for_chat(
                    db, agent_id
                )
                if agent_data is None:
                    return "找不到这个 companion，请确认 agent_id 是否正确。"

            session_id = generate_session_id(str(chat_id))
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
                    runtime_channel=CompanionRuntimeChannel.TELEGRAM,
                )
            reply = turn.assistant_text.strip()
            if reply:
                self._coordinator.remove_foreground_pending(preset_uid)
                return reply
            if turn.tool_background_started:
                ev = await self._coordinator.background_events.get()
                self._coordinator.pop_foreground_pending(ev.user_msg_uuid)
                tool_reply = ev.text.strip()
                if tool_reply:
                    return tool_reply
            self._coordinator.remove_foreground_pending(preset_uid)
            return "（没有回复内容）"
        except Exception:
            logger.exception(
                "telegram inprocess user_chat failed user_id={} agent_id={}",
                user_id,
                agent_id,
            )
            self._coordinator.remove_foreground_pending(preset_uid)
            return "Companion 回合失败，请查看 Ops 日志。"

    async def _push_telegram_assistant_text(self, text: str) -> None:
        assert self._downlink is not None
        await self._downlink.send_assistant_text(text)

    async def _tool_background_consumer(self) -> None:
        assert self._downlink is not None
        while True:
            ev = await self._coordinator.background_events.get()
            ctx = self._coordinator.pop_foreground_pending(ev.user_msg_uuid)
            if ctx is None:
                logger.warning(
                    "telegram tool_bg missing foreground ctx user_msg_uuid={}",
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
                logger.exception("telegram tool_bg deliver failed")
