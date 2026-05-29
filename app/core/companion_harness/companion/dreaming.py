"""Sleeping-state dreaming for turning recent chat into memory.

Dreaming is Inty's sleeping-state memory activity. When the user has not sent
messages for more than two hours, the background dreaming scheduler reviews the
chat since the previous dream and settles it into applicable MemoryDocs.

If there has never been a previous dream, Inty only looks back over the last
24 hours so the first dream does not reopen an unbounded history.

Dreaming is separate from inner tick: inner tick is for awake internal activity,
while dreaming is for asleep background consolidation. Dreaming does not send a
message to the user and does not alter the original visible chat history.

The dream settles chat into documents such as the raw diary, day summary,
long-term memory, user understanding, communication style, and durable
relationship/personality boundaries. After a dream succeeds, Inty records a
checkpoint so future LLM calls do not carry raw chat before that checkpoint;
the next conversation continues from the consolidated memories instead.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.companion_harness.experience_profile.context_mode import (
    experience_profile_allows_maintenance_inner_tick,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)

from .models import (
    ChatMessage,
    load_context_meta,
    load_transcript_from_store,
    transcript_rows_for_public_chat_llm,
    transcript_without_trailing_presence_signals,
)

_FIRST_DREAMING_LOOKBACK = timedelta(hours=24)


class DreamingState(BaseModel):
    """Persistent boundary for the latest successful sleeping-state dream."""

    model_config = ConfigDict(frozen=True)

    last_processed_main_line_count: int = Field(ge=0)
    last_processed_main_uuid: str
    last_processed_at: datetime
    last_processed_latest_user_ts: datetime
    last_processed_calendar_date: datetime

    @field_validator(
        "last_processed_at",
        "last_processed_latest_user_ts",
        "last_processed_calendar_date",
    )
    @classmethod
    def _normalize_aware_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class DreamingCandidate:
    """Transcript rows selected for one dream, plus the boundary to checkpoint."""

    rows: list[ChatMessage]
    latest_user_ts: datetime
    boundary_line_count: int
    boundary_uuid: str


def parse_transcript_datetime(raw: str) -> datetime:
    """Parse transcript ``ts`` values as timezone-aware UTC datetimes."""
    assert raw
    normalized = raw.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_dreaming_state(store: MemoryStore) -> DreamingState | None:
    """Read the dreaming checkpoint document when present."""
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.dreaming_state_json
    body = store.read_document_if_exists(rel)
    if body is None or not body.strip():
        return None
    return DreamingState.model_validate_json(body)


def save_dreaming_state(store: MemoryStore, state: DreamingState) -> None:
    """Persist the dreaming checkpoint document."""
    rel = DEFAULT_MEMORY_STORE_SCOPE_PATHS.dreaming_state_json
    store.write_document(rel, state.model_dump_json(indent=2) + "\n")


def dreaming_state_from_candidate(
    candidate: DreamingCandidate,
    *,
    processed_at: datetime,
) -> DreamingState:
    """Build the checkpoint state for a successfully processed candidate."""
    assert candidate.rows
    processed_utc = _aware_utc(processed_at)
    return DreamingState(
        last_processed_main_line_count=candidate.boundary_line_count,
        last_processed_main_uuid=candidate.boundary_uuid,
        last_processed_at=processed_utc,
        last_processed_latest_user_ts=candidate.latest_user_ts,
        last_processed_calendar_date=processed_utc,
    )


def apply_dreaming_checkpoint_to_prompt_rows(
    rows: list[ChatMessage],
    state: DreamingState | None,
) -> list[ChatMessage]:
    """Remove dialogue at or before the latest dreaming checkpoint."""
    if state is None:
        return rows
    checkpoint_uuid = state.last_processed_main_uuid
    if not checkpoint_uuid:
        return rows
    for idx, row in enumerate(rows):
        if row.uuid == checkpoint_uuid:
            return rows[idx + 1 :]
    return rows


def dreaming_candidate_slice(
    store: MemoryStore,
    *,
    now: datetime,
) -> DreamingCandidate | None:
    """Return checkpoint-after rows, or at most the last 24h when no checkpoint exists."""
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    raw_rows = transcript_without_trailing_presence_signals(
        load_transcript_from_store(store, paths.transcript)
    )
    if not raw_rows:
        return None
    state = load_dreaming_state(store)
    start_idx = _start_index_after_checkpoint(raw_rows, state)
    cutoff = _aware_utc(now) - _FIRST_DREAMING_LOOKBACK
    if state is None:
        while start_idx < len(raw_rows):
            if parse_transcript_datetime(raw_rows[start_idx].ts) >= cutoff:
                break
            start_idx += 1
    candidate_raw = raw_rows[start_idx:]
    if not candidate_raw:
        return None
    candidate_public = transcript_rows_for_public_chat_llm(candidate_raw)
    if not candidate_public:
        return None
    real_users = [m for m in candidate_public if is_real_user_message(m)]
    if not real_users:
        return None
    latest_user_ts = max(parse_transcript_datetime(m.ts) for m in real_users)
    boundary = candidate_public[-1]
    boundary_uuid = boundary.uuid or ""
    if not boundary_uuid:
        return None
    return DreamingCandidate(
        rows=candidate_public,
        latest_user_ts=latest_user_ts,
        boundary_line_count=start_idx + len(candidate_raw),
        boundary_uuid=boundary_uuid,
    )


def dreaming_due(
    store: MemoryStore,
    *,
    now: datetime,
    dreaming_idle_seconds: int,
) -> DreamingCandidate | None:
    """Return a candidate only when the scope is in sleeping-state idle."""
    assert dreaming_idle_seconds > 0
    if not experience_profile_allows_maintenance_inner_tick(
        load_context_meta(store=store).context_mode
    ):
        return None
    candidate = dreaming_candidate_slice(store, now=now)
    if candidate is None:
        return None
    idle = _aware_utc(now) - candidate.latest_user_ts
    if idle.total_seconds() < dreaming_idle_seconds:
        return None
    return candidate


def dreaming_race_guard_matches(
    store: MemoryStore,
    candidate: DreamingCandidate,
) -> bool:
    """True when no later transcript row appeared after this dream input."""
    fresh = dreaming_candidate_slice(store, now=datetime.now(timezone.utc))
    if fresh is None:
        return False
    return (
        fresh.boundary_line_count == candidate.boundary_line_count
        and fresh.boundary_uuid == candidate.boundary_uuid
        and fresh.latest_user_ts == candidate.latest_user_ts
    )


def is_real_user_message(message: ChatMessage) -> bool:
    """True for human-authored user transcript rows."""
    return (
        message.role == "user"
        and message.presence is None
        and message.inner_tick is not True
        and message.proactive_chat is not True
        and message.scheduled is not True
    )


def _start_index_after_checkpoint(
    raw_rows: list[ChatMessage],
    state: DreamingState | None,
) -> int:
    if state is None:
        return 0
    count = state.last_processed_main_line_count
    if 0 < count <= len(raw_rows):
        boundary = raw_rows[count - 1]
        if boundary.uuid == state.last_processed_main_uuid:
            return count
    for idx, row in enumerate(raw_rows):
        if row.uuid == state.last_processed_main_uuid:
            return idx + 1
    return len(raw_rows)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
