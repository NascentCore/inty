"""Persist one ``LoopDeliverable`` to transcript JSONL on enqueue."""

from __future__ import annotations

import uuid

from app.core.companion_harness.companion.transcript_assistant_row import (
    TranscriptAssistantRowBuildInput,
    append_transcript_assistant_row,
)
from app.core.companion_harness.companion.utc import utc_iso_ts

from app.core.companion_harness.tools.tool_background import ToolOutputEvent

from .loop_deliverable import LoopDeliverable, LoopDeliverableKind
from .output_queue_types import OutputQueueTranscriptContext, ToolTranscriptDigest


def persist_deliverable_transcript(
    deliverable: LoopDeliverable,
    *,
    transcript_ctx: OutputQueueTranscriptContext,
) -> None:
    """Append one assistant row when ``deliverable`` maps to transcript storage."""
    row = _transcript_row_build_input(deliverable, transcript_ctx=transcript_ctx)
    if row is None:
        return
    append_transcript_assistant_row(
        transcript_ctx.store,
        transcript_ctx.transcript_rel,
        row,
        ts=utc_iso_ts(),
    )


def _transcript_row_build_input(
    deliverable: LoopDeliverable,
    *,
    transcript_ctx: OutputQueueTranscriptContext,
) -> TranscriptAssistantRowBuildInput | None:
    match deliverable.kind:
        case (
            LoopDeliverableKind.INTERIM_REPLY
            | LoopDeliverableKind.BOOTSTRAP_INTERIM
        ):
            interim = deliverable.bootstrap_interim
            assert interim is not None
            assistant_msg_uuid = interim.assistant_msg_uuid or str(uuid.uuid4())
            return TranscriptAssistantRowBuildInput(
                content=deliverable.assistant_text,
                uuid=assistant_msg_uuid,
                reply_to=transcript_ctx.user_msg_uuid,
                trace_id=transcript_ctx.trace_id,
                source="chat",
                significance_perception=None,
                turn_recall=None,
                tool_results_digest=None,
            )
        case LoopDeliverableKind.FOREGROUND_TEXT | LoopDeliverableKind.USER_REPLY:
            assert deliverable.assistant_text.strip()
            return TranscriptAssistantRowBuildInput(
                content=deliverable.assistant_text,
                uuid=str(uuid.uuid4()),
                reply_to=transcript_ctx.user_msg_uuid,
                trace_id=transcript_ctx.trace_id,
                source="chat",
                significance_perception=deliverable.significance_meta,
                turn_recall=deliverable.turn_recall,
                tool_results_digest=None,
            )
        case LoopDeliverableKind.TOOL_BACKGROUND:
            event = deliverable.tool_output
            assert event is not None
            digest = _tool_digest_from_event(event)
            return TranscriptAssistantRowBuildInput(
                content=deliverable.assistant_text,
                uuid=event.assistant_msg_uuid,
                reply_to=transcript_ctx.user_msg_uuid,
                trace_id=transcript_ctx.trace_id,
                source="tool_bg",
                significance_perception=deliverable.significance_meta,
                turn_recall=deliverable.turn_recall,
                tool_results_digest=digest,
            )
        case _:
            raise AssertionError(f"unknown deliverable kind: {deliverable.kind}")


def _tool_digest_from_event(event: ToolOutputEvent) -> ToolTranscriptDigest | None:
    raw = event.tool_results_digest
    if raw is None or not raw.strip():
        return None
    return ToolTranscriptDigest(body=raw.strip())
