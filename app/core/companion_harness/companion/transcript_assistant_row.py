"""Shared Pydantic write model for assistant rows on transcript JSONL (#3407)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

from app.core.companion_harness.memory.memory_store import MemoryStore

if TYPE_CHECKING:
    from app.core.companion_harness.loop.output_queue_types import ToolTranscriptDigest


@dataclass(frozen=True)
class TranscriptAssistantRowBuildInput:
    """Inputs to build one assistant transcript JSONL record."""

    content: str
    uuid: str
    reply_to: str
    trace_id: str
    source: str
    significance_perception: dict[str, Any] | None
    turn_recall: str | None
    tool_results_digest: ToolTranscriptDigest | None


class TranscriptAssistantRow(BaseModel):
    """Wire shape for one assistant line in ``transcript*.jsonl``."""

    role: Literal["assistant"] = "assistant"
    content: str
    ts: str
    uuid: str
    reply_to: str
    source: str
    trace_id: str
    significance_perception: dict[str, Any] | None = Field(
        default=None,
        description="Dual-LLM envelope importance triple when present.",
    )
    turn_recall: str | None = Field(
        default=None,
        description="Ephemeral Turn Brief when non-empty (#3342).",
    )
    tool_results_digest: dict[str, str] | None = Field(
        default=None,
        description="Structured tool-result digest on the same row as display content.",
    )


def build_transcript_assistant_row(
    row_input: TranscriptAssistantRowBuildInput,
    *,
    ts: str,
) -> dict[str, Any]:
    """Validate and serialize one assistant JSONL object (omit unset optional keys)."""

    digest_payload: dict[str, str] | None = None
    if row_input.tool_results_digest is not None:
        digest_payload = {"body": row_input.tool_results_digest.body}
    row = TranscriptAssistantRow(
        content=row_input.content,
        ts=ts,
        uuid=row_input.uuid,
        reply_to=row_input.reply_to,
        source=row_input.source,
        trace_id=row_input.trace_id,
        significance_perception=row_input.significance_perception,
        turn_recall=row_input.turn_recall,
        tool_results_digest=digest_payload,
    )
    return row.model_dump(mode="json", exclude_none=True)


def append_transcript_assistant_row(
    store: MemoryStore,
    transcript_relative_path: str,
    row_input: TranscriptAssistantRowBuildInput,
    *,
    ts: str,
) -> None:
    store.append_jsonl_record(
        transcript_relative_path,
        build_transcript_assistant_row(row_input, ts=ts),
    )
