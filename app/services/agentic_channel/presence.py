"""In-process agent-channel presence: shared inner-tick + tool_bg per scope.

TODO(!3490): Remove queue USER_CHAT ``foreground_pending`` + ``background_sink``.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    is_im_runtime_channel,
)
from app.core.config import global_config_loaded_from_config_yaml
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.schemas.chat import ChatCompletionRequest, ChatMessage
from app.services import agent_service
from app.services.agentic_channel.channel_runtime import (
    get_scope_channel_registry,
)
from app.services.agentic_channel.scope_queue_serving import (
    ScopeDrainCompletion,
    ScopeQueueServing,
)
from app.core.companion_harness.agentic_companion.output_queue import (
    OutputDeliveryUnroutableError,
    OutputQueueAppendInput,
    ReadyOutputMessage,
    get_output_queue_for_scope,
    ready_output_is_agent_initiated_visible,
)
from app.core.companion_harness.agentic_companion.types import (
    InboundWireMessage,
)
from app.core.companion_harness.companion.models import (
    user_visible_assistant_text,
)
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.services.agentic_companion.downlink import (
    DownlinkKind,
    agent_initiated_visible_downlink,
    queue_user_reply_downlink,
    tool_background_downlink,
)
from app.services.agentic_companion.inner_tick_poll import run_inner_tick_poll
from app.core.companion_harness.companion.utc import (
    strip_leading_transcript_timestamp_prefixes,
)
from app.services.agentic_channel.provision import resolve_chat_model_for_scope
from app.services.agentic_channel.serving import enqueue_inbound_wire_message
from app.services.companion_chat_service import (
    run_companion_implicit_sign_on_greeting_turn_for_api,
)
from app.services.agentic_companion.session import Coordinator, Session
from app.services.chat_service import generate_session_id

_SIGN_ON_GREETING_USER_TEXT = (
    "The user opened the Telegram chat through onboarding."
)

_IM_USER_NOT_FOUND = "Could not find your Inty user. Please send /start again."
_IM_AGENT_NOT_FOUND = "Could not find this companion. Please check the agent."
_IM_TURN_FAILED = "Companion turn failed. Please check Ops logs."


def _localized_im_channel_message(
    runtime_channel: ChannelKind,
    *,
    english: str,
    chinese: str,
) -> str:
    """Return English copy on IM channels; Chinese elsewhere."""
    match runtime_channel:
        case channel if is_im_runtime_channel(channel):
            return english
        case _:
            return chinese


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
        self._queue_serving: ScopeQueueServing | None = None

    @property
    def scope(self) -> AgentScope:
        return self._scope

    @property
    def coordinator(self) -> Coordinator:
        return self._coordinator

    async def start(self) -> None:
        if self._session is not None:
            return
        synthetic_chat_id = self._scope.memory_store_chat_id()
        self._coordinator.store_inner_tick_coords(
            user_id=self._scope.user_id,
            agent_id=self._scope.agent_id,
            chat_id=synthetic_chat_id,
        )
        self._session = Session.from_coordinator(
            downlink=_NoopSessionDownlink(),
            coordinator=self._coordinator,
        )
        poll_secs = float(
            global_config_loaded_from_config_yaml.agent.companion_harness.inner_tick.proactive_chat.poll_seconds
        )

        async def _run_poll(_ctx: dict) -> None:
            registry = get_scope_channel_registry(self._scope)
            active = registry.active_channel()
            if active is None:
                return
            adapter = registry.adapters.get(active)
            if adapter is None:
                return
            delivery = adapter.inner_tick_delivery()
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
        registry = get_scope_channel_registry(self._scope)
        initial_channel = registry.active_channel()
        if initial_channel is None:
            initial_channel = ChannelKind.APP_WS
        self._queue_serving = ScopeQueueServing(
            self._scope,
            background_output_sink=self._coordinator.background_sink,
            deliver_message=self._deliver_ready_via_active_channel,
            on_drain_complete=self._on_queue_drain_complete,
            runtime_channel=initial_channel,
        )
        await self._queue_serving.start()

    async def stop(self) -> None:
        if self._queue_serving is not None:
            await self._queue_serving.stop()
            self._queue_serving = None
        task = self._tool_bg_task
        if task is not None and (not task.done()):
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self._tool_bg_task = None
        if self._session is not None:
            await self._session.stop()
            self._session = None
        self._coordinator.sign_out()

    async def _deliver_ready_via_active_channel(
        self, message: ReadyOutputMessage
    ) -> None:
        text = strip_leading_transcript_timestamp_prefixes(message.text.strip())
        if not text:
            return
        if (
            not ready_output_is_agent_initiated_visible(message)
            and not message.message_ids
        ):
            raise OutputDeliveryUnroutableError(
                self._scope,
                message.message_ids,
            )
        registry = get_scope_channel_registry(self._scope)
        active = registry.active_channel()
        if active is None:
            raise RuntimeError(
                f"no ACTIVE channel for output scope={self._scope.registry_key()}"
            )
        downlink = registry.downlinks.get(active)
        if downlink is None:
            raise RuntimeError(
                f"no downlink for channel={active.value} "
                f"scope={self._scope.registry_key()}"
            )
        if ready_output_is_agent_initiated_visible(message):
            # TODO(#3576): Deliver agent-initiated sign-on rows on App-WS via OutputQueue.
            if not is_im_runtime_channel(active):
                raise OutputDeliveryUnroutableError(
                    self._scope,
                    message.message_ids,
                )
            event = agent_initiated_visible_downlink(
                assistant_text=text,
                output_message=message,
            )
        else:
            event = queue_user_reply_downlink(
                assistant_text=text,
                message_ids=message.message_ids,
                output_message=message,
            )
        await downlink.deliver(event)

    async def greet_on_sign_on(self, *, runtime_channel: ChannelKind) -> None:
        """Run implicit sign-on greeting and append visible text to OutputQueue."""
        assert runtime_channel is not None
        model = await resolve_chat_model_for_scope(self._scope)
        bundle = ImplicitSignalBundle(
            client_time=None,
            user_signed_on=True,
            server_received_at_utc=datetime.now(timezone.utc),
        )
        turn = await run_companion_implicit_sign_on_greeting_turn_for_api(
            user_id=self._scope.user_id,
            agent_id=self._scope.agent_id,
            chat_id=self._scope.memory_store_chat_id(),
            user_text=_SIGN_ON_GREETING_USER_TEXT,
            resolved_chat_model=model,
            implicit_signal_bundle=bundle,
            runtime_channel=runtime_channel,
        )
        visible = user_visible_assistant_text(turn.assistant_text)
        if visible is None:
            return
        output_queue = get_output_queue_for_scope(self._scope)
        await output_queue.append_visible_message(
            OutputQueueAppendInput(
                kind=DownlinkKind.USER_REPLY,
                batch_id="",
                text=visible,
                message_ids=(),
                trace_id=None,
                langsmith_trace_id=None,
                langsmith_run_id=None,
                turn_recall=None,
            )
        )

    async def enqueue_app_ws_user_turn(
        self,
        *,
        wire_id: str,
        user_text: str,
        client_message_id: str | None,
        local_id: str | None,
        chat_history_user_row_id: int | None,
    ) -> str:
        # TODO(#3566): gate enqueue + wake when token budget exhausted (avoid durable backlog).
        """Enqueue one App WS user message and wake scope queue worker."""
        assert wire_id != ""
        assert user_text.strip() != ""
        inbound = InboundWireMessage(
            scope=self._scope,
            channel=ChannelKind.APP_WS,
            wire_id=wire_id,
            text=user_text.strip(),
            received_at_utc=datetime.now(timezone.utc),
            client_message_id=client_message_id,
            local_id=local_id,
            chat_history_user_row_id=chat_history_user_row_id,
        )
        queue_message_id = await enqueue_inbound_wire_message(inbound)
        assert self._queue_serving is not None
        self._queue_serving.wake(runtime_channel=ChannelKind.APP_WS)
        return queue_message_id

    async def _on_queue_drain_complete(
        self, completion: ScopeDrainCompletion
    ) -> None:
        input_message_ids = completion.input_message_ids
        assert input_message_ids
        if completion.tool_background_started:
            primary_message_id = input_message_ids[-1]
            for message_id in input_message_ids:
                if message_id != primary_message_id:
                    self._coordinator.remove_foreground_pending(message_id)
            return
        for message_id in input_message_ids:
            self._coordinator.remove_foreground_pending(message_id)

    # TODO(channel-inbound-envelope): Accept reply-to + reaction fields; map channel message
    # IDs ↔ transcript UUIDs — epic #3440; Telegram #3441; Weixin #3442
    async def handle_user_text(
        self,
        user_text: str,
        *,
        runtime_channel: ChannelKind,
    ) -> str:
        """Run one user-chat turn; return Channel error text or ``""`` when delivered via queue."""
        stripped = user_text.strip()
        assert stripped
        queue_message_id: str | None = None
        try:
            async with AsyncSessionLocal() as db:
                inty_user_row = await db.execute(
                    select(User).where(User.id == self._scope.user_id)
                )
                inty_user = inty_user_row.scalar_one_or_none()
                if inty_user is None:
                    return _localized_im_channel_message(
                        runtime_channel,
                        english=_IM_USER_NOT_FOUND,
                        chinese="无法找到你的 Inty 用户，请重新 /start。",
                    )
                agent_data = await agent_service.get_agent_for_chat(
                    db, self._scope.agent_id
                )
                if agent_data is None:
                    return _localized_im_channel_message(
                        runtime_channel,
                        english=_IM_AGENT_NOT_FOUND,
                        chinese="找不到这个 companion，请确认 agent_id 是否正确。",
                    )

            synthetic_chat_id = self._scope.memory_store_chat_id()
            if self._coordinator.snapshot_inner_tick_coords() is None:
                self._coordinator.store_inner_tick_coords(
                    user_id=self._scope.user_id,
                    agent_id=self._scope.agent_id,
                    chat_id=synthetic_chat_id,
                )
            session_id = generate_session_id(synthetic_chat_id)
            wire_id = f"{runtime_channel.value}:{self._scope.registry_key()}"
            inbound = InboundWireMessage(
                scope=self._scope,
                channel=runtime_channel,
                wire_id=wire_id,
                text=stripped,
                received_at_utc=datetime.now(timezone.utc),
                client_message_id=None,
            )
            # TODO(!3411): Telegram Bot API has no device timezone; manual E2E smoke:
            # inference → update_user_md → USER.md → LangSmith foreground ## User's Local Time Context.
            queue_message_id = await enqueue_inbound_wire_message(inbound)
            stub_request = ChatCompletionRequest(
                messages=[ChatMessage(role="user", content=stripped)],
                message_id=queue_message_id,
            )
            self._coordinator.set_foreground_pending(
                queue_message_id,
                {
                    "session_id": session_id,
                    "agent_id": self._scope.agent_id,
                    "user_id": self._scope.user_id,
                    "chat_id": synthetic_chat_id,
                    "request": stub_request,
                    "effective_local_id": None,
                },
            )
            assert self._queue_serving is not None
            self._queue_serving.wake(runtime_channel=runtime_channel)
            return ""
        except Exception as exc:
            logger.exception(
                "agent_channel user_chat failed scope={}",
                self._scope.registry_key(),
            )
            if queue_message_id is not None and not getattr(
                exc, "companion_tool_background_started", False
            ):
                self._coordinator.remove_foreground_pending(queue_message_id)
            return _localized_im_channel_message(
                runtime_channel,
                english=_IM_TURN_FAILED,
                chinese="Companion 回合失败，请查看 Ops 日志。",
            )

    async def _tool_background_consumer(self) -> None:
        while True:
            ev = await self._coordinator.background_events.get()
            registry = get_scope_channel_registry(self._scope)
            active = registry.active_channel()
            if active == ChannelKind.APP_WS:
                downlink = registry.downlinks.get(active)
                if downlink is None:
                    continue
                try:
                    await downlink.deliver(
                        tool_background_downlink(tool_output=ev)
                    )
                except Exception:
                    logger.exception("agent_channel tool_bg deliver failed")
                continue
            ctx = self._coordinator.pop_foreground_pending(ev.user_msg_uuid)
            if ctx is None:
                logger.warning(
                    "agent_channel tool_bg missing foreground ctx user_msg_uuid={}",
                    ev.user_msg_uuid,
                )
                continue
            self._coordinator.set_foreground_pending(ev.user_msg_uuid, ctx)
            if not ev.output_to_user:
                continue
            try:
                if active is None:
                    continue
                downlink = registry.downlinks.get(active)
                if downlink is None:
                    continue
                await downlink.deliver(tool_background_downlink(tool_output=ev))
                self._coordinator.remove_foreground_pending(ev.user_msg_uuid)
            except Exception:
                logger.exception("agent_channel tool_bg deliver failed")


class _NoopSessionDownlink:
    """Session compatibility shim; Telegram agent text is emitted via OutputQueue."""

    async def deliver(self, event) -> None:
        _ = event


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
    # TODO(#3567): call on token-budget pause; contrast with sign_out-only channel teardown.
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
