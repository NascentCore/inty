"""APP WebSocket helpers for the agentic companion serving pipeline.

Per-scope ``ScopeQueueServing`` wakes on enqueue; inbound handlers return after
Postgres commit. Delivery uses a per-turn ``send_text`` registered on the scope.

TODO(!3488): ``AppWsChannelAdapter`` on ``turn_channel_up`` + one ``Coordinator`` per scope
on ``AgentChannelPresence``; retire this WS-local queue registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import TYPE_CHECKING, Any

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.types import (
    InboundWireMessage,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.core.companion_harness.companion.turn_routes import (
    BackgroundToolEventSink,
)
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.services.agentic_channel.scope_queue_serving import (
    OnDrainCompleteFn,
    ScopeDrainCompletion,
    ScopeQueueServing,
)
from app.services.agentic_channel.serving import (
    SendTextFn,
    enqueue_inbound_wire_message,
)
from app.services.agentic_channel.turn import ensure_memory_store_session
from app.services.agentic_companion.ws_turn_support import (
    image_asset_baseline_for_scope_store,
)

if TYPE_CHECKING:
    from app.core.companion_harness.memory.memory_store import MemoryStore


@dataclass
class AppWsQueueDeliveryFlags:
    """Mutable delivery state shared between enqueue, drain, and send_text."""

    queue_message_id: str = ""
    tool_background_started: bool = False
    image_asset_baseline: int = 0
    image_asset_baseline_initialized: bool = False
    memory_store: MemoryStore | None = None


@dataclass(frozen=True)
class AppWsUserTurnQueueInput:
    """One App WS user-chat turn routed through durable InputQueue/OutputQueue."""

    scope: AgentScope
    wire_id: str
    user_text: str
    client_message_id: str | None
    implicit_signal_bundle: ImplicitSignalBundle
    background_output_sink: BackgroundToolEventSink | None
    delivery_flags: AppWsQueueDeliveryFlags
    send_text: SendTextFn


@dataclass(frozen=True)
class AppWsUserTurnEnqueueResult:
    """Outcome of enqueue + wake without awaiting drain or OutputQueue delivery."""

    queue_message_id: str


@dataclass
class _AppWsScopeTurnDelivery:
    """Per-turn WS delivery hooks; updated before each enqueue + wake."""

    send_text: SendTextFn | None = None
    delivery_flags: AppWsQueueDeliveryFlags | None = None
    client_message_id: str | None = None
    companion_ws_foreground_pending: dict[str, dict[str, Any]] | None = None


_scope_turn_delivery: dict[str, _AppWsScopeTurnDelivery] = {}
_scope_queue_serving: dict[str, ScopeQueueServing] = {}
_registry_lock = Lock()


def clear_app_ws_scope_queue_for_tests() -> None:
    """Drop WS scope queue registries (tests only)."""
    with _registry_lock:
        _scope_turn_delivery.clear()
        _scope_queue_serving.clear()


def _scope_key(scope: AgentScope) -> str:
    return scope.registry_key()


def _scope_turn_state(scope: AgentScope) -> _AppWsScopeTurnDelivery:
    key = _scope_key(scope)
    with _registry_lock:
        state = _scope_turn_delivery.get(key)
        if state is None:
            state = _AppWsScopeTurnDelivery()
            _scope_turn_delivery[key] = state
        return state


async def _scope_send_text(scope: AgentScope, text: str) -> None:
    state = _scope_turn_state(scope)
    assert state.send_text is not None
    await state.send_text(text)


async def _on_app_ws_scope_drain_complete(
    scope: AgentScope,
    completion: ScopeDrainCompletion,
) -> None:
    state = _scope_turn_state(scope)
    flags = state.delivery_flags
    assert flags is not None
    flags.tool_background_started = completion.tool_background_started
    pending = state.companion_ws_foreground_pending
    client_message_id = state.client_message_id
    queue_message_id = flags.queue_message_id
    if pending is None or client_message_id is None:
        return
    if completion.tool_background_started:
        primary_message_id = completion.input_message_ids[-1]
        for message_id in completion.input_message_ids:
            if message_id != primary_message_id:
                pending.pop(message_id, None)
        pending.pop(client_message_id, None)
        return
    pending.pop(client_message_id, None)
    if queue_message_id:
        pending.pop(queue_message_id, None)


def _make_on_drain_complete(scope: AgentScope) -> OnDrainCompleteFn:
    async def on_drain_complete(completion: ScopeDrainCompletion) -> None:
        await _on_app_ws_scope_drain_complete(scope, completion)

    return on_drain_complete


async def _ensure_app_ws_scope_queue_serving(
    scope: AgentScope,
    *,
    background_output_sink,
) -> ScopeQueueServing:
    key = _scope_key(scope)
    with _registry_lock:
        existing = _scope_queue_serving.get(key)
        if existing is not None:
            return existing

        async def send_text(text: str) -> None:
            await _scope_send_text(scope, text)

        serving = ScopeQueueServing(
            scope,
            background_output_sink=background_output_sink,
            send_text=send_text,
            on_drain_complete=_make_on_drain_complete(scope),
        )
        _scope_queue_serving[key] = serving
        created = serving
    await created.start()
    return created


async def stop_app_ws_scope_queue_serving(scope: AgentScope) -> None:
    """Stop per-scope WS queue workers (WS disconnect / agent lease release)."""
    key = _scope_key(scope)
    with _registry_lock:
        serving = _scope_queue_serving.pop(key, None)
        _scope_turn_delivery.pop(key, None)
    if serving is not None:
        await serving.stop()


async def enqueue_app_ws_user_turn_and_wake(
    queue_input: AppWsUserTurnQueueInput,
    *,
    companion_ws_foreground_pending: dict[str, dict[str, Any]] | None,
) -> AppWsUserTurnEnqueueResult:
    """Enqueue one WS user message and wake scope queue worker; do not await drain."""
    assert queue_input.wire_id != ""
    assert queue_input.user_text.strip() != ""
    inbound = InboundWireMessage(
        scope=queue_input.scope,
        channel=CompanionRuntimeChannel.APP,
        wire_id=queue_input.wire_id,
        text=queue_input.user_text.strip(),
        received_at_utc=datetime.now(timezone.utc),
        client_message_id=queue_input.client_message_id,
    )
    queue_message_id = await enqueue_inbound_wire_message(inbound)
    queue_input.delivery_flags.queue_message_id = queue_message_id
    session = await ensure_memory_store_session(queue_input.scope)
    queue_input.delivery_flags.image_asset_baseline = (
        image_asset_baseline_for_scope_store(session.store)
    )
    queue_input.delivery_flags.image_asset_baseline_initialized = True
    queue_input.delivery_flags.memory_store = session.store

    turn_state = _scope_turn_state(queue_input.scope)
    turn_state.send_text = queue_input.send_text
    turn_state.delivery_flags = queue_input.delivery_flags
    turn_state.client_message_id = queue_input.client_message_id
    turn_state.companion_ws_foreground_pending = companion_ws_foreground_pending

    serving = await _ensure_app_ws_scope_queue_serving(
        queue_input.scope,
        background_output_sink=queue_input.background_output_sink,
    )
    serving.wake(runtime_channel=CompanionRuntimeChannel.APP)
    return AppWsUserTurnEnqueueResult(queue_message_id=queue_message_id)
