"""APP WebSocket helpers for the agentic companion serving pipeline.

Per-scope ``ScopeQueueServing`` wakes on enqueue; inbound handlers return after
Postgres commit. Delivery hooks are registered per input ``queue_message_id`` so
concurrent enqueues on one scope cannot overwrite each other's drain completion
or OutputQueue send routing.

Routing hooks outlive drain completion: the foreground reply is appended to the
OutputQueue during the turn and the background tool loop appends later replies
under the same input ids, both delivered asynchronously by the output pump. Drain
completion therefore only clears the foreground-pending waiter; it must not drop
the send routing, or the pump would race the input worker and lose those replies.
Routing is dropped only when scope serving stops (WS teardown), which is safe
because one ``AsyncSession`` is bound per connection.

TODO(!3488): ``AppWsChannelAdapter`` on ``turn_channel_up`` + one ``Coordinator`` per scope
on ``AgentChannelPresence``; retire this WS-local queue registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import TYPE_CHECKING, Any

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.output_queue import (
    OutputDeliveryUnroutableError,
    ReadyOutputMessage,
)
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
    DeliverReadyMessageFn,
    enqueue_inbound_wire_message,
)
from app.services.agentic_companion.ws_turn_support import (
    image_asset_baseline_for_scope_store,
)
from app.services.agentic_channel.session import ensure_memory_store_session

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
    send_text: DeliverReadyMessageFn


@dataclass(frozen=True)
class AppWsUserTurnEnqueueResult:
    """Outcome of enqueue + wake without awaiting drain or OutputQueue delivery."""

    queue_message_id: str


@dataclass(frozen=True)
class _AppWsScopeTurnDelivery:
    """Per input-queue message WS delivery hooks."""

    send_text: DeliverReadyMessageFn
    delivery_flags: AppWsQueueDeliveryFlags
    client_message_id: str | None
    companion_ws_foreground_pending: dict[str, dict[str, Any]] | None


_scope_turn_delivery: dict[str, dict[str, _AppWsScopeTurnDelivery]] = {}
_scope_queue_serving: dict[str, ScopeQueueServing] = {}
_registry_lock = Lock()


def clear_app_ws_scope_queue_for_tests() -> None:
    """Drop WS scope queue registries (tests only)."""
    with _registry_lock:
        _scope_turn_delivery.clear()
        _scope_queue_serving.clear()


def _scope_key(scope: AgentScope) -> str:
    return scope.registry_key()


def _register_scope_turn_delivery(
    scope: AgentScope,
    queue_message_id: str,
    *,
    send_text: DeliverReadyMessageFn,
    delivery_flags: AppWsQueueDeliveryFlags,
    client_message_id: str | None,
    companion_ws_foreground_pending: dict[str, dict[str, Any]] | None,
) -> None:
    assert queue_message_id != ""
    key = _scope_key(scope)
    with _registry_lock:
        per_scope = _scope_turn_delivery.setdefault(key, {})
        per_scope[queue_message_id] = _AppWsScopeTurnDelivery(
            send_text=send_text,
            delivery_flags=delivery_flags,
            client_message_id=client_message_id,
            companion_ws_foreground_pending=companion_ws_foreground_pending,
        )


def _lookup_scope_turn_delivery(
    scope: AgentScope,
    queue_message_id: str,
) -> _AppWsScopeTurnDelivery | None:
    key = _scope_key(scope)
    with _registry_lock:
        return _scope_turn_delivery.get(key, {}).get(queue_message_id)


def _pop_scope_turn_delivery(scope: AgentScope, queue_message_id: str) -> None:
    key = _scope_key(scope)
    with _registry_lock:
        per_scope = _scope_turn_delivery.get(key)
        if per_scope is None:
            return
        per_scope.pop(queue_message_id, None)
        if not per_scope:
            _scope_turn_delivery.pop(key, None)


def _lookup_scope_turn_delivery_for_output(
    scope: AgentScope,
    message_ids: tuple[str, ...],
) -> _AppWsScopeTurnDelivery | None:
    for message_id in message_ids:
        state = _lookup_scope_turn_delivery(scope, message_id)
        if state is not None:
            return state
    return None


async def _scope_deliver_ready_output(
    scope: AgentScope,
    message: ReadyOutputMessage,
) -> None:
    state = _lookup_scope_turn_delivery_for_output(scope, message.message_ids)
    if state is None:
        raise OutputDeliveryUnroutableError(scope, message.message_ids)
    await state.send_text(message)


def _clear_turn_foreground_pending(
    state: _AppWsScopeTurnDelivery,
    *,
    queue_message_id: str,
    drop_client_alias: bool,
    drop_queue_alias: bool,
) -> None:
    pending = state.companion_ws_foreground_pending
    if pending is None:
        return
    if drop_client_alias:
        client_message_id = state.client_message_id
        if client_message_id is not None:
            pending.pop(client_message_id, None)
    if drop_queue_alias and state.delivery_flags.queue_message_id:
        pending.pop(state.delivery_flags.queue_message_id, None)
    if not drop_client_alias and not drop_queue_alias:
        pending.pop(queue_message_id, None)


async def _on_app_ws_scope_drain_complete(
    scope: AgentScope,
    completion: ScopeDrainCompletion,
) -> None:
    input_message_ids = completion.input_message_ids
    assert input_message_ids
    if completion.tool_background_started:
        primary_message_id = input_message_ids[-1]
        for message_id in input_message_ids:
            state = _lookup_scope_turn_delivery(scope, message_id)
            if state is None:
                continue
            state.delivery_flags.tool_background_started = True
            if message_id != primary_message_id:
                _clear_turn_foreground_pending(
                    state,
                    queue_message_id=message_id,
                    drop_client_alias=True,
                    drop_queue_alias=True,
                )
                _pop_scope_turn_delivery(scope, message_id)
            else:
                _clear_turn_foreground_pending(
                    state,
                    queue_message_id=message_id,
                    drop_client_alias=True,
                    drop_queue_alias=False,
                )
        return
    for message_id in input_message_ids:
        state = _lookup_scope_turn_delivery(scope, message_id)
        if state is None:
            continue
        state.delivery_flags.tool_background_started = False
        _clear_turn_foreground_pending(
            state,
            queue_message_id=message_id,
            drop_client_alias=True,
            drop_queue_alias=True,
        )
        # Keep send routing until WS scope teardown so the output pump can deliver
        # trailing foreground lines appended before drain completion returns.


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

        async def deliver_message(message: ReadyOutputMessage) -> None:
            await _scope_deliver_ready_output(scope, message)

        serving = ScopeQueueServing(
            scope,
            background_output_sink=background_output_sink,
            deliver_message=deliver_message,
            on_drain_complete=_make_on_drain_complete(scope),
            runtime_channel=CompanionRuntimeChannel.APP,
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

    _register_scope_turn_delivery(
        queue_input.scope,
        queue_message_id,
        send_text=queue_input.send_text,
        delivery_flags=queue_input.delivery_flags,
        client_message_id=queue_input.client_message_id,
        companion_ws_foreground_pending=companion_ws_foreground_pending,
    )

    serving = await _ensure_app_ws_scope_queue_serving(
        queue_input.scope,
        background_output_sink=queue_input.background_output_sink,
    )
    serving.wake(runtime_channel=CompanionRuntimeChannel.APP)
    return AppWsUserTurnEnqueueResult(queue_message_id=queue_message_id)
