"""Sleeping-state dreaming for end-of-day rollup into memory.

Dreaming is Inty's sleeping-state memory activity. When the configured idle
period passes with no user messages, a signed-on presence inner-tick poll may
**summarize everything that happened during the day** since the previous dream
checkpoint and settle it into applicable MemoryDocs: user-visible dialogue on
``transcript.jsonl`` (``USER_CHAT``, ``PROACTIVE_CHAT``, ``SCHEDULED``) plus
silent awake inner-tick footprints (``AUTONOMY``, ``MAINTENANCE`` — inner-tick
transcript, ``LIFE_CURRENTS.md``, ``ai_private.jsonl``, related tool/jsonl traces).

``TODO(dreaming-day-rollup)``: ``dreaming_candidate_slice`` today gates on
``transcript.jsonl`` only; merge inner-tick / ai_private / LIFE_CURRENTS into
``consolidate_memory_during_dreaming`` input (#3343; optional #3366).

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

**Cadence (intentional):** at most **one successful dream per scope per UTC calendar
day** (``dreaming_due`` compares ``DreamingState.last_processed_calendar_date`` to
``now``). Same-day chat after a morning dream waits until the next UTC day even when
``dreaming_idle_seconds`` is satisfied. User-local timezone for the day boundary is
planned (``TODO(user-feature)``).

Concurrency: ``InnerTickActivity.DREAMING`` runs on the inner-tick poll path under
presence ``Coordinator.turn_lock`` (same wire as user chat and other inner ticks).
Prototype assumes **single presence** per scope (``companion_harness`` AGENTS.md) — scope
``CompanionSession.turn_lock`` serializes turns (#3272).

TODO(scope-inner-tick-worker): Dreaming must run for idle scopes without signed-on
presence (#3255 — https://github.com/NascentCore/inty/issues/3255). It is not a delivery
track — hoist to scope-level inner-tick worker with ``CompanionSession`` ``turn_lock``
(and cluster advisory lock for multi-process — #3271
https://github.com/NascentCore/inty/issues/3271), not the per-wire poll in
``inner_tick_poll.py``.

Prototype invariant: ``transcript.jsonl`` must not change while a dreaming batch runs
(``turn_lock`` + ``dreaming_idle_seconds`` ≫ tool_background timeouts; #3272 single
presence; #3271 cluster lock). ``dreaming_race_guard_matches`` re-checks that invariant;
``run_dreaming_batch_if_due`` raises on mismatch — not a soft retry path.

TODO(dreaming-transcript-invariant): If ``dreaming_idle_seconds`` is lowered below
tool_background worst-case runtime, gate dreaming on ``tool_bg_idle`` or revisit this
assumption (see #3123).


TODO(companion-package-reorg): Move this module into a focused sub-package under companion_harness (see issue body for draft layout).
https://github.com/NascentCore/inty/issues/3409"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)

from .models import (
    ChatMessage,
    load_context_meta,
    load_transcript_from_store,
    transcript_without_trailing_presence_signals,
)
from .transcript_anchor import parse_transcript_row_ts as parse_transcript_datetime

_FIRST_DREAMING_LOOKBACK = timedelta(hours=24)


class DreamingState(BaseModel):
    """Persistent boundary for the latest successful sleeping-state dream."""

    model_config = ConfigDict(frozen=True)

    last_processed_main_line_count: int = Field(ge=0)
    last_processed_main_uuid: str
    last_processed_at: datetime
    last_processed_latest_user_ts: datetime
    last_processed_calendar_date: datetime = Field(
        description=(
            "UTC calendar date of the last successful dream; "
            "``dreaming_due`` skips further dreams on the same UTC day (intentional)."
        ),
    )

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
    """Return checkpoint-after rows for dreaming consolidation.

    Today only ``transcript.jsonl`` (user-visible chat, proactive, scheduled).
    TODO(dreaming-day-rollup): Merge same-day ``transcript_inner_tick.jsonl``
    (AUTONOMY / MAINTENANCE), ``LIFE_CURRENTS.md``, and related tool/jsonl traces
    into the candidate slice passed to ``consolidate_memory_during_dreaming``;
    extend ``DreamingCandidate`` / race guard if inner-tick boundaries need separate
    checkpoints (#3376). Partial ai_private render (manifest hydrate + unconsumed
    section) shipped in #3420 — candidate **selection** still main transcript only.

    Without checkpoint: at most the last 24h on the main transcript.
    """
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    # TODO(dreaming-day-rollup): merge paths.transcript_inner_tick + LIFE_CURRENTS.md
    # into candidate rows; ai_private dreaming render partial in #3420 (#3376).
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
    candidate_rows = raw_rows[start_idx:]
    if not candidate_rows:
        return None
    real_users = [m for m in candidate_rows if is_real_user_message(m)]
    if not real_users:
        return None
    latest_user_ts = max(parse_transcript_datetime(m.ts) for m in real_users)
    boundary = candidate_rows[-1]
    boundary_uuid = boundary.uuid or ""
    if not boundary_uuid:
        return None
    return DreamingCandidate(
        rows=candidate_rows,
        latest_user_ts=latest_user_ts,
        boundary_line_count=start_idx + len(candidate_rows),
        boundary_uuid=boundary_uuid,
    )


def dreaming_due(
    store: MemoryStore,
    *,
    now: datetime,
    dreaming_idle_seconds: int,
) -> DreamingCandidate | None:
    """Return a candidate only when the scope is in sleeping-state.

    Gates (all must pass):

    - Bootstrap complete.
    - **At most one dream per UTC calendar day** when a checkpoint exists (expected
      product behavior; not a bug).
    - ``dreaming_idle_seconds`` elapsed since the latest real user message in the slice.
    - Non-empty candidate slice after the last checkpoint.

    Day boundary uses UTC because user/client timezone is not always known.
    """
    assert dreaming_idle_seconds > 0
    now_utc = _aware_utc(now)
    if not load_context_meta(
        store=store
    ).workspace_bootstrap_user_interactive_completed:
        return None
    state = load_dreaming_state(store)
    if (
        state is not None
        and state.last_processed_calendar_date.date() == now_utc.date()
    ):
        # Intentional: one successful dream per scope per UTC calendar day.
        # TODO(user-feature): Use user/client's timezone for the day boundary.
        return None
    candidate = dreaming_candidate_slice(store, now=now)
    if candidate is None:
        return None
    idle = now_utc - candidate.latest_user_ts
    if idle.total_seconds() < dreaming_idle_seconds:
        return None
    return candidate


class DreamingTranscriptBoundaryMismatchError(RuntimeError):
    """``transcript.jsonl`` boundary changed during a dreaming batch (invariant violation)."""


def dreaming_race_guard_matches(
    store: MemoryStore,
    candidate: DreamingCandidate,
) -> bool:
    """Return whether the dream-input slice boundary is unchanged since batch start.

    Recomputes ``dreaming_candidate_slice`` and compares ``boundary_line_count``,
    ``boundary_uuid``, and ``latest_user_ts`` to ``candidate``. Under prototype
    assumptions (see module doc), this should always match after
    ``consolidate_memory_during_dreaming``; ``run_dreaming_batch_if_due`` raises
    ``DreamingTranscriptBoundaryMismatchError`` when it does not.
    """
    fresh = dreaming_candidate_slice(store, now=datetime.now(timezone.utc))
    if fresh is None:
        return False
    return (
        fresh.boundary_line_count == candidate.boundary_line_count
        and fresh.boundary_uuid == candidate.boundary_uuid
        and fresh.latest_user_ts == candidate.latest_user_ts
    )


def assert_dreaming_transcript_boundary_unchanged(
    store: MemoryStore,
    candidate: DreamingCandidate,
) -> None:
    """Raise when ``transcript.jsonl`` changed during a dreaming batch."""
    if dreaming_race_guard_matches(store, candidate):
        return
    raise DreamingTranscriptBoundaryMismatchError(
        "transcript.jsonl boundary changed during dreaming batch "
        f"boundary_uuid={candidate.boundary_uuid!r} "
        f"boundary_line_count={candidate.boundary_line_count}"
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
