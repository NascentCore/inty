"""In-process companion presence for Weixin demo bridge (no ``/api/v1/chat/ws`` loopback).

Not WeChat user presence: iLink does not expose open-app or open-DM signals (see ``transport``).

TODO(!3493): Migrate ``WeixinInprocessPresence`` to ``ScopeQueueServing`` enqueue + wake (!3487).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from loguru import logger

from app.api import deps
from app.core.config import global_config_loaded_from_config_yaml
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.schemas.chat import ChatCompletionRequest, ChatMessage
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.core.companion_harness.companion.scope_turn_lock import (
    companion_scope_from_foreground_ctx,
    get_scope_turn_lock,
)
from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.types import (
    InboundWireMessage,
)
from app.services import agent_service
from app.core.companion_harness.agentic_companion.output_queue import (
    ReadyOutputMessage,
)
from app.core.companion_harness.companion.utc import (
    strip_leading_transcript_timestamp_prefixes,
)
from app.services.agentic_channel.serving import (
    drain_and_deliver_user_chat_turn,
    enqueue_inbound_wire_message,
)
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
        """Store agent-channel inner-tick coords, start poll + tool_bg consumer.

        Inner-tick shares ``AgentScope.memory_store_chat_id()`` with ``handle_user_text``
        so proactive/scheduled ticks read the same MemoryStore transcript as user chat.
        """
        assert transport is not None
        inty_user = await _inty_user_from_binding(self._binding)
        if inty_user is None:
            raise RuntimeError(
                "weixin inprocess presence: invalid or expired inty_jwt for demo bridge"
            )
        self._inty_user_id = str(inty_user.id)
        agent_id = self._binding.agent_id
        # TODO(!3350): Share AgentScope inner-tick coord setup with AgentChannelPresence.start().
        scope = AgentScope(user_id=self._inty_user_id, agent_id=agent_id)
        synthetic_chat_id = scope.memory_store_chat_id()
        self._coordinator.store_inner_tick_coords(
            user_id=self._inty_user_id,
            agent_id=agent_id,
            chat_id=synthetic_chat_id,
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
            global_config_loaded_from_config_yaml.agent.companion_harness.inner_tick.proactive_chat.poll_seconds
        )
        delivery = inner_tick_delivery_for_weixin(
            self._push_weixin_assistant_text
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

    # TODO(weixin-inbound-image): Phase 2 — rename to ``handle_user_turn``; accept
    # https://github.com/NascentCore/inty/issues/3293
    # ``CompanionUserTurnInput`` and call ``run_user_chat(user_turn=...)``. Image-only
    # turns need non-empty ``image_data_urls`` even when ``text`` is empty.
    async def handle_user_text(self, user_text: str) -> str:
        """Run one user-chat turn via queues; return Channel error or ``""`` when delivered.

        Happy-path assistant text is sent by ``drain_and_deliver_user_chat_turn`` through
        ``WeixinDownlink``; Hermes transport must not re-send the return value.
        """
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
        queue_message_id: str | None = None
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
                agent_data = await agent_service.get_agent_for_chat(
                    db, agent_id
                )
                if agent_data is None:
                    return "Companion not found for this bridge."

            scope = AgentScope(user_id=user_id, agent_id=agent_id)
            synthetic_chat_id = scope.memory_store_chat_id()
            session_id = generate_session_id(synthetic_chat_id)
            wire_id = f"weixin:{self._binding.user_id}"
            inbound = InboundWireMessage(
                scope=scope,
                channel=CompanionRuntimeChannel.WECHAT_WEIXIN,
                wire_id=wire_id,
                text=stripped,
                received_at_utc=datetime.now(timezone.utc),
                client_message_id=None,
            )
            queue_message_id = await enqueue_inbound_wire_message(inbound)
            stub_request = ChatCompletionRequest(
                messages=[ChatMessage(role="user", content=stripped)],
                message_id=queue_message_id,
            )
            self._coordinator.set_foreground_pending(
                queue_message_id,
                {
                    "session_id": session_id,
                    "agent_id": agent_id,
                    "user_id": user_id,
                    "chat_id": synthetic_chat_id,
                    "request": stub_request,
                    "effective_local_id": None,
                },
            )
            implicit_bundle = ImplicitSignalBundle(
                client_time=None,
                user_signed_on=False,
                server_received_at_utc=datetime.now(timezone.utc),
            )

            async def deliver_weixin_message(
                message: ReadyOutputMessage,
            ) -> None:
                assert self._downlink is not None
                text = strip_leading_transcript_timestamp_prefixes(
                    message.text.strip()
                )
                if not text:
                    return
                await self._downlink.send_assistant_text(text)

            delivery_result = await drain_and_deliver_user_chat_turn(
                scope,
                runtime_channel=CompanionRuntimeChannel.WECHAT_WEIXIN,
                delivery_wire_id=wire_id,
                implicit_signal_bundle=implicit_bundle,
                background_output_sink=self._coordinator.background_sink,
                deliver_message=deliver_weixin_message,
            )
            if not delivery_result.tool_background_started:
                self._coordinator.remove_foreground_pending(queue_message_id)
            return ""
        except Exception as exc:
            logger.exception(
                "weixin inprocess user_chat failed user_id={} agent_id={}",
                user_id,
                agent_id,
            )
            if queue_message_id is not None and not getattr(
                exc, "companion_tool_background_started", False
            ):
                self._coordinator.remove_foreground_pending(queue_message_id)
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
            scope = companion_scope_from_foreground_ctx(ctx)
            if scope is None:
                logger.warning(
                    "weixin tool_bg missing scope coords user_msg_uuid={}",
                    ev.user_msg_uuid,
                )
                continue
            scope_lock = get_scope_turn_lock(scope)
            try:
                async with scope_lock:
                    await self._downlink.deliver(
                        tool_background_downlink(tool_output=ev)
                    )
            except Exception:
                logger.exception("weixin tool_bg deliver failed")
