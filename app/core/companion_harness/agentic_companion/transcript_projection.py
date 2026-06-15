"""Project queue records into MemoryStore transcript.jsonl."""

from __future__ import annotations

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)

from .types import (
    AgentOutputMessage,
    TranscriptProjectionRecord,
    UserInputMessage,
)


class MemoryStoreTranscriptProjector:
    """Write transcript rows linked to queue message ids."""

    async def project_input(
        self,
        *,
        store: MemoryStore,
        record: UserInputMessage,
    ) -> None:
        projection = TranscriptProjectionRecord(
            queue_message_id=record.message_id,
            queue_kind="input",
            role="user",
            content=record.text,
            timestamp=record.received_at_utc.replace(microsecond=0).isoformat(),
            trace_id=None,
            reply_to=record.client_message_id,
        )
        self._append(store, projection)

    async def project_output(
        self,
        *,
        store: MemoryStore,
        record: AgentOutputMessage,
    ) -> None:
        projection = TranscriptProjectionRecord(
            queue_message_id=record.message_id,
            queue_kind="output",
            role="assistant",
            content=record.text,
            timestamp=record.created_at_utc.replace(microsecond=0).isoformat(),
            trace_id=record.trace_id,
            reply_to=(
                record.in_reply_to_input_ids[0]
                if record.in_reply_to_input_ids
                else None
            ),
        )
        self._append(store, projection)

    def _append(
        self,
        store: MemoryStore,
        projection: TranscriptProjectionRecord,
    ) -> None:
        paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
        store.append_jsonl_record(
            paths.transcript,
            {
                "role": projection.role,
                "content": projection.content,
                "ts": projection.timestamp,
                "uuid": projection.queue_message_id,
                "queue_kind": projection.queue_kind,
                "trace_id": projection.trace_id,
                "reply_to": projection.reply_to,
            },
        )
