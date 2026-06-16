"""Shared write helper for user rows on transcript JSONL."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel

from app.core.companion_harness.memory.memory_store import MemoryStore


@dataclass(frozen=True)
class TranscriptUserRowBuildInput:
    """Inputs to build one user transcript JSONL record."""

    content: str
    uuid: str
    trace_id: str


class TranscriptUserRow(BaseModel):
    """Wire shape for one user line in ``transcript*.jsonl``."""

    role: Literal["user"] = "user"
    content: str
    ts: str
    uuid: str
    trace_id: str


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
    )
    return row.model_dump(mode="json")


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
