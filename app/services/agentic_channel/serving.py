"""Agentic companion serving pipeline glue for Channel/Wire integrations."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from loguru import logger

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.companion import (
    AgenticCompanion,
)
from app.core.companion_harness.agentic_companion.postgres_queue import (
    PostgresInputQueueRepository,
    PostgresOutputQueueRepository,
)
from app.core.companion_harness.agentic_companion.types import (
    InboundWireMessage,
    QueueAck,
    QueueMessageId,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.core.companion_harness.companion.utc import (
    strip_leading_transcript_timestamp_prefixes,
)
from app.db.session import AsyncSessionLocal
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.services.agentic_companion.downlink import (
    Downlink,
    downlink_delivers_user_visible_text,
)
from app.services.agentic_channel.provision import resolve_chat_model_for_scope

SendTextFn = Callable[[str], Awaitable[None]]


@dataclass(frozen=True)
class DrainScopeOnceResult:
    """Outcome of one synchronous companion drain for Channel/Wire callers."""

    reply_text: str
    tool_background_started: bool


@dataclass(frozen=True)
class UserChatTurnDeliveryResult:
    """Outcome of one user-chat enqueue + drain + OutputQueue pull delivery."""

    delivered_text: str
    tool_background_started: bool


async def drain_and_deliver_user_chat_turn(
    scope: AgentScope,
    *,
    runtime_channel: CompanionRuntimeChannel,
    delivery_wire_id: str,
    implicit_signal_bundle: ImplicitSignalBundle,
    background_output_sink,
    send_text: SendTextFn,
) -> UserChatTurnDeliveryResult:
    """Drain one input batch, pull OutputQueue, deliver via ``send_text``."""
    # TODO(#3402): Return typed Channel handle result instead of str from presence.
    assert delivery_wire_id != ""
    drain_result = await drain_scope_once_via_companion(
        scope,
        runtime_channel=runtime_channel,
        implicit_signal_bundle=implicit_signal_bundle,
        background_output_sink=background_output_sink,
    )
    delivered_text = await deliver_pending_output_for_wire(
        scope,
        delivery_channel=runtime_channel,
        delivery_wire_id=delivery_wire_id,
        send_text=send_text,
    )
    return UserChatTurnDeliveryResult(
        delivered_text=delivered_text,
        tool_background_started=drain_result.tool_background_started,
    )


async def enqueue_inbound_wire_message(
    inbound: InboundWireMessage,
) -> str:
    """Append one pending user message to durable InputQueue."""
    async with AsyncSessionLocal() as db:
        input_repo = PostgresInputQueueRepository(db)
        user_msg = await input_repo.append_user_message(inbound)
        await db.commit()
        return user_msg.message_id


async def drain_scope_once_via_companion(
    scope: AgentScope,
    *,
    runtime_channel: CompanionRuntimeChannel,
    implicit_signal_bundle: ImplicitSignalBundle,
    background_output_sink,
) -> DrainScopeOnceResult:
    """Drain one input batch; return user-visible text and tool_bg ownership."""
    model = await resolve_chat_model_for_scope(scope)
    async with AsyncSessionLocal() as db:
        companion = AgenticCompanion(
            scope=scope,
            input_repo=PostgresInputQueueRepository(db),
            output_repo=PostgresOutputQueueRepository(db),
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
        )
    reply = strip_leading_transcript_timestamp_prefixes(
        result.assistant_text.strip()
    )
    if reply:
        return DrainScopeOnceResult(
            reply_text=reply,
            tool_background_started=result.tool_background_started,
        )
    if result.tool_background_started:
        return DrainScopeOnceResult(
            reply_text="",
            tool_background_started=True,
        )
    return DrainScopeOnceResult(
        reply_text="（没有回复内容）",
        tool_background_started=False,
    )


async def deliver_pending_output_for_wire(
    scope: AgentScope,
    *,
    delivery_channel: CompanionRuntimeChannel,
    delivery_wire_id: str,
    send_text: SendTextFn,
    limit: int = 16,
) -> str:
    """Pull OutputQueue rows, send via ``send_text``, return last user-visible text."""
    assert delivery_wire_id != ""
    last_reply = ""
    async with AsyncSessionLocal() as db:
        output_repo = PostgresOutputQueueRepository(db)
        claims = await output_repo.claim_pending_for_delivery(
            scope,
            delivery_channel=delivery_channel,
            delivery_wire_id=delivery_wire_id,
            limit=limit,
        )
        for claim in claims:
            record = claim.record
            downlink = Downlink(
                kind=record.kind,
                assistant_text=record.text,
                turn=None,
                tool_output=None,
                bootstrap_interim=None,
                scheduled_task_id=None,
                transcript_user_text=None,
            )
            if not downlink_delivers_user_visible_text(downlink):
                await output_repo.mark_delivered(
                    QueueAck(
                        message_id=QueueMessageId(value=record.message_id),
                        delivered_at_utc=datetime.now(timezone.utc),
                    )
                )
                continue
            text = strip_leading_transcript_timestamp_prefixes(
                record.text.strip()
            )
            if not text:
                await output_repo.mark_delivered(
                    QueueAck(
                        message_id=QueueMessageId(value=record.message_id),
                        delivered_at_utc=datetime.now(timezone.utc),
                    )
                )
                continue
            try:
                await send_text(text)
                await output_repo.mark_delivered(
                    QueueAck(
                        message_id=QueueMessageId(value=record.message_id),
                        delivered_at_utc=datetime.now(timezone.utc),
                    )
                )
                last_reply = text
            except Exception as exc:
                logger.warning(
                    "output delivery failed scope={} message_id={} error={}",
                    scope.registry_key(),
                    record.message_id,
                    exc,
                )
                await output_repo.mark_failed(
                    record.message_id,
                    error_message=repr(exc),
                )
        await db.commit()
    return last_reply


async def handle_sync_user_turn_via_queues(
    scope: AgentScope,
    *,
    inbound: InboundWireMessage,
    runtime_channel: CompanionRuntimeChannel,
    implicit_signal_bundle: ImplicitSignalBundle,
    background_output_sink,
    send_text: SendTextFn,
) -> UserChatTurnDeliveryResult:
    """Enqueue inbound user text, drain one batch, pull OutputQueue for delivery."""
    await enqueue_inbound_wire_message(inbound)
    return await drain_and_deliver_user_chat_turn(
        scope,
        runtime_channel=runtime_channel,
        delivery_wire_id=inbound.wire_id,
        implicit_signal_bundle=implicit_signal_bundle,
        background_output_sink=background_output_sink,
        send_text=send_text,
    )
