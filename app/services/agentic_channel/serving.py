"""Agentic companion serving pipeline glue for Channel/Wire integrations."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from loguru import logger

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.companion import (
    AgenticCompanion,
)
from app.core.companion_harness.agentic_companion.output_queue import (
    OutputDeliveryAck,
    OutputDeliveryFailure,
    OutputDeliverySkip,
    OutputDeliveryUnroutableError,
    ReadyOutputMessage,
    get_output_queue_for_scope,
)
from app.core.companion_harness.agentic_companion.postgres_queue import (
    PostgresInputQueueRepository,
)
from app.core.companion_harness.agentic_companion.types import (
    InboundWireMessage,
)
from app.core.companion_harness.agent_channel.gateway import (
    GatewayKind,
)
from app.core.companion_harness.companion.utc import (
    strip_leading_transcript_timestamp_prefixes,
)
from app.db.session import AsyncSessionLocal
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.services.agentic_channel.provision import resolve_chat_model_for_scope

DeliverReadyMessageFn = Callable[[ReadyOutputMessage], Awaitable[None]]
DeliveryTargetResolver = Callable[[], tuple[GatewayKind | None, str | None]]

_CHANNEL_OUTPUT_PUMP_POLL_SEC = 0.02


@dataclass(frozen=True)
class DrainScopeOnceResult:
    """Outcome of processing at most one claimed inbound batch for a scope.

    When a batch was drained, carries the inbound message ids and whether a
    background tool loop took over. When nothing was pending, reports no drain.
    """

    reply_text: str
    tool_background_started: bool
    batch_drained: bool
    input_message_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.batch_drained:
            assert self.input_message_ids
        else:
            assert not self.input_message_ids


@dataclass(frozen=True)
class UserChatTurnDeliveryResult:
    """Outcome of one user-chat enqueue + drain + OutputQueue pull delivery."""

    delivered_text: str
    tool_background_started: bool


async def _deliver_ready_message(
    *,
    message: ReadyOutputMessage,
    deliver_message: DeliverReadyMessageFn,
    scope: AgentScope,
) -> str | None:
    text = strip_leading_transcript_timestamp_prefixes(message.text.strip())
    if not text:
        output_queue = get_output_queue_for_scope(scope)
        await output_queue.ack_delivered(
            OutputDeliveryAck(
                message_id=message.message_id,
                delivered_at_utc=datetime.now(timezone.utc),
            )
        )
        return None
    try:
        await deliver_message(message)
    except OutputDeliveryUnroutableError as exc:
        logger.warning(
            "output delivery unroutable scope={} message_id={} error={}",
            scope.registry_key(),
            message.message_id,
            exc,
        )
        output_queue = get_output_queue_for_scope(scope)
        await output_queue.skip_delivery(
            OutputDeliverySkip(
                message_id=message.message_id,
                error_message=repr(exc),
            )
        )
        return None
    except Exception as exc:
        logger.warning(
            "output delivery failed scope={} message_id={} error={}",
            scope.registry_key(),
            message.message_id,
            exc,
        )
        output_queue = get_output_queue_for_scope(scope)
        await output_queue.mark_delivery_failed(
            OutputDeliveryFailure(
                message_id=message.message_id,
                error_message=repr(exc),
            )
        )
        return None
    output_queue = get_output_queue_for_scope(scope)
    await output_queue.ack_delivered(
        OutputDeliveryAck(
            message_id=message.message_id,
            delivered_at_utc=datetime.now(timezone.utc),
        )
    )
    return text


async def channel_output_pump(
    scope: AgentScope,
    *,
    deliver_message: DeliverReadyMessageFn,
    stop_event: asyncio.Event,
    delivery_channel: GatewayKind | None = None,
    delivery_wire_id: str | None = None,
    resolve_delivery_target: DeliveryTargetResolver | None = None,
    poll_interval_sec: float = _CHANNEL_OUTPUT_PUMP_POLL_SEC,
) -> str:
    """Pull in-memory ready OutputQueue messages until ``stop_event`` and queue drained."""
    assert poll_interval_sec > 0.0
    assert deliver_message is not None
    output_queue = get_output_queue_for_scope(scope)

    def _delivery_target() -> tuple[GatewayKind | None, str | None]:
        if resolve_delivery_target is not None:
            return resolve_delivery_target()
        return delivery_channel, delivery_wire_id

    last_reply = ""
    while not stop_event.is_set():
        channel, wire_id = _delivery_target()
        for message in await output_queue.pull_ready_batch(
            delivery_channel=channel,
            delivery_wire_id=wire_id,
        ):
            delivered = await _deliver_ready_message(
                message=message,
                deliver_message=deliver_message,
                scope=scope,
            )
            if delivered is not None:
                last_reply = delivered
        await asyncio.sleep(poll_interval_sec)
    channel, wire_id = _delivery_target()
    for message in await output_queue.pull_ready_batch(
        delivery_channel=channel,
        delivery_wire_id=wire_id,
    ):
        delivered = await _deliver_ready_message(
            message=message,
            deliver_message=deliver_message,
            scope=scope,
        )
        if delivered is not None:
            last_reply = delivered
    return last_reply


async def flush_scope_output_queue_ready(
    scope: AgentScope,
    *,
    deliver_message: DeliverReadyMessageFn,
) -> None:
    """Deliver every ready OutputQueue message once (no polling sleep).

    Test and one-shot paths only. Do not call while ``ScopeQueueServing`` runs its
    output pump on the same scope — concurrent flush and pump duplicate delivery.
    """
    assert deliver_message is not None
    output_queue = get_output_queue_for_scope(scope)
    while True:
        batch = await output_queue.pull_ready_batch()
        if not batch:
            break
        for message in batch:
            await _deliver_ready_message(
                message=message,
                deliver_message=deliver_message,
                scope=scope,
            )


async def drain_and_deliver_user_chat_turn(
    scope: AgentScope,
    *,
    runtime_channel: GatewayKind,
    delivery_wire_id: str,
    implicit_signal_bundle: ImplicitSignalBundle,
    background_output_sink,
    deliver_message: DeliverReadyMessageFn,
) -> UserChatTurnDeliveryResult:
    """Drain one input batch while pumping OutputQueue ready messages."""
    # TODO(#3493): Remove when Weixin migrates; ScopeQueueServing owns drain+pump (#3487; App-WS landed in pull/3512).
    # TODO(!3402): Return typed Channel handle result instead of str from presence.
    assert delivery_wire_id != ""

    stop_event = asyncio.Event()
    pump_task = asyncio.create_task(
        channel_output_pump(
            scope,
            deliver_message=deliver_message,
            stop_event=stop_event,
            delivery_channel=runtime_channel,
            delivery_wire_id=delivery_wire_id,
        ),
        name=f"channel_output_pump_{scope.registry_key()}",
    )
    try:
        drain_result = await drain_scope_once_via_companion(
            scope,
            runtime_channel=runtime_channel,
            implicit_signal_bundle=implicit_signal_bundle,
            background_output_sink=background_output_sink,
        )
    finally:
        stop_event.set()
        delivered_text = await pump_task
    return UserChatTurnDeliveryResult(
        delivered_text=delivered_text,
        tool_background_started=drain_result.tool_background_started,
    )


async def enqueue_inbound_wire_message(
    inbound: InboundWireMessage,
) -> str:
    # TODO(#3566): reject before durable InputQueue write when token budget exhausted.
    """Append one pending user message to durable InputQueue."""
    async with AsyncSessionLocal() as db:
        input_repo = PostgresInputQueueRepository(db)
        user_msg = await input_repo.append_user_message(inbound)
        await db.commit()
        return user_msg.message_id


async def drain_scope_once_via_companion(
    scope: AgentScope,
    *,
    runtime_channel: GatewayKind,
    implicit_signal_bundle: ImplicitSignalBundle,
    background_output_sink,
) -> DrainScopeOnceResult:
    """Drain one input batch; return user-visible text and tool_bg ownership."""
    model = await resolve_chat_model_for_scope(scope)
    async with AsyncSessionLocal() as db:
        companion = AgenticCompanion(
            scope=scope,
            input_repo=PostgresInputQueueRepository(db),
        )
        try:
            result = await companion.drain_once(
                resolved_chat_model=model,
                runtime_channel=runtime_channel,
                background_output_sink=background_output_sink,
                implicit_signal_bundle=implicit_signal_bundle,
            )
        except Exception:
            # Persist mark_batch_failed before the session context rolls back.
            await db.commit()
            raise
        await db.commit()
    if result is None:
        return DrainScopeOnceResult(
            reply_text="",
            tool_background_started=False,
            batch_drained=False,
            input_message_ids=(),
        )
    reply = strip_leading_transcript_timestamp_prefixes(
        result.assistant_text.strip()
    )
    return DrainScopeOnceResult(
        reply_text=reply,
        tool_background_started=result.tool_background_started,
        batch_drained=True,
        input_message_ids=result.input_message_ids,
    )


async def handle_sync_user_turn_via_queues(
    scope: AgentScope,
    *,
    inbound: InboundWireMessage,
    runtime_channel: GatewayKind,
    implicit_signal_bundle: ImplicitSignalBundle,
    background_output_sink,
    deliver_message: DeliverReadyMessageFn,
) -> UserChatTurnDeliveryResult:
    """Enqueue inbound user text, drain one batch, pull OutputQueue for delivery."""
    await enqueue_inbound_wire_message(inbound)
    return await drain_and_deliver_user_chat_turn(
        scope,
        runtime_channel=runtime_channel,
        delivery_wire_id=inbound.wire_id,
        implicit_signal_bundle=implicit_signal_bundle,
        background_output_sink=background_output_sink,
        deliver_message=deliver_message,
    )
