"""Transcript context and structured tool digest for ``OutputQueue`` enqueue."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.companion_harness.memory.memory_store import MemoryStore


@dataclass(frozen=True)
class OutputQueueTranscriptContext:
    """Immutable transcript write context bound to one user turn."""

    store: MemoryStore
    transcript_rel: str
    user_msg_uuid: str
    trace_id: str


@dataclass(frozen=True)
class ToolTranscriptDigest:
    """Structured tool-result digest on the same JSONL row as display ``content``."""

    body: str
