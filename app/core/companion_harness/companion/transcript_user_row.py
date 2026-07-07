"""Shared helper for writing user lines to companion transcript storage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel

from app.core.companion_harness.memory.memory_store import MemoryStore

from .models import InnerTickKind


@dataclass(frozen=True)
class TranscriptUserRowBuildInput:
    """Source fields for one user line in the conversation transcript."""

    content: str
    uuid: str
    trace_id: str
    inner_tick_kind: InnerTickKind | None = None


class TranscriptUserRow(BaseModel):
    """Validated shape of one user message stored in transcript JSONL."""

    role: Literal["user"] = "user"
    content: str
    ts: str
    uuid: str
    trace_id: str
    inner_tick_kind: InnerTickKind | None = None


def build_transcript_user_row(
    row_input: TranscriptUserRowBuildInput,
    *,
    ts: str,
) -> dict[str, Any]:
    """Validate and serialize one user JSONL object."""
    row = TranscriptUserRow(
        content=row_input.content,
        ts=ts,
        uuid=row_input.uuid,
        trace_id=row_input.trace_id,
        inner_tick_kind=row_input.inner_tick_kind,
    )
    return row.model_dump(mode="json", exclude_none=True)


def append_transcript_user_row(
    store: MemoryStore,
    transcript_relative_path: str,
    row_input: TranscriptUserRowBuildInput,
    *,
    ts: str,
) -> None:
    """Append one user row before in-turn assistant emissions."""
    store.append_jsonl_record(
        transcript_relative_path,
        build_transcript_user_row(row_input, ts=ts),
    )
