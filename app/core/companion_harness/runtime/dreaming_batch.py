"""DreamingBatch orchestration: single entry for sleeping-state memory consolidation.

Generated entirely by Cursor agent for Phase 3.4 runtime seam slice.

``run_dreaming_batch_if_due`` is the only DreamingBatch orchestrator. Callers
(``companion_chat_service``, inner-tick fire) resolve ``CompanionSession`` and
hold ``turn_lock`` before calling here. See ``runtime`` package docstring for the
lock contract.

TODO(#3634): Future persona PromptPlan + AgenticLoop entry for dreaming consolidation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.companion_harness.companion.bootstrap_memdoc_policy import (
    resolve_bootstrap_memdoc_policy,
)
from app.core.companion_harness.companion.dreaming import (
    DreamingCandidate,
    assert_dreaming_transcript_boundary_unchanged,
    dreaming_due,
    inception_dream_due,
    dreaming_state_from_candidate,
    save_dreaming_state,
)
from app.core.companion_harness.companion.dreaming_observability import (
    DreamingBatchOutcome,
    dreaming_batch_langsmith_scope,
    new_dreaming_batch_trace_id,
    record_dreaming_batch_observability,
)
from app.core.companion_harness.companion.manager import CompanionSession
from app.core.companion_harness.memory.dreaming_consolidation import (
    DREAMING_ONE_SHOT_LLM_ROLE,
    consolidate_memory_during_dreaming,
)
from app.core.companion_harness.runtime.dreaming_scope_lock import (
    try_dreaming_scope_advisory_lock,
)
from app.utils.config import DreamingCuratorMode


def run_dreaming_batch_if_due(
    session: CompanionSession,
    *,
    idle_seconds: int,
    curator_mode: DreamingCuratorMode,
) -> DreamingBatchOutcome:
    """Run one sleeping-state dreaming batch when due.

    ``dreaming_due`` enforces idle time plus **at most one successful dream per UTC
    calendar day** per scope (intentional; see ``companion.dreaming``).

    Caller must hold scope ``CompanionSession.turn_lock`` (single WebSocket presence). Re-checks ``dreaming_due`` inside the lock so conditions may change while waiting.
    Prototype: ``transcript.jsonl`` must not change during the batch; mismatch after
    ``consolidate_memory_during_dreaming`` raises ``DreamingTranscriptBoundaryMismatchError``
    (see ``companion.dreaming`` module doc — #3271, tool_bg timing TODO).
    TODO(dreaming-day-rollup): inner-tick merge may require boundary guard on — #3376
    ``transcript_inner_tick.jsonl`` too (#3376).

    Multi-process: repository-backed stores acquire a Postgres advisory lock per scope
    before consolidation; contention yields ``DreamingBatchOutcome.ADVISORY_LOCK_BUSY``.

    Callable from scope inner-tick worker (#3255 / PR #3387); caller holds scope
    ``turn_lock`` on ``CompanionSession``.
    """
    assert idle_seconds > 0
    if not session.is_initialized:
        return DreamingBatchOutcome.NOT_DUE

    now = datetime.now(UTC)
    policy = resolve_bootstrap_memdoc_policy()
    candidate = inception_dream_due(
        session.store,
        now=now,
        policy=policy,
    )
    if candidate is None:
        candidate = dreaming_due(
            session.store,
            now=now,
            dreaming_idle_seconds=idle_seconds,
        )
    if candidate is None:
        return DreamingBatchOutcome.NOT_DUE

    inty_trace_id = new_dreaming_batch_trace_id()

    if session.store.uses_repository_without_scope_disk:
        with try_dreaming_scope_advisory_lock(
            session.store.scope.registry_key()
        ) as lock_acquired:
            if not lock_acquired:
                record_dreaming_batch_observability(
                    session=session,
                    inty_trace_id=inty_trace_id,
                    outcome=DreamingBatchOutcome.ADVISORY_LOCK_BUSY,
                    candidate=candidate,
                    langsmith_root_run=None,
                )
                return DreamingBatchOutcome.ADVISORY_LOCK_BUSY
            return _run_dreaming_batch_locked(
                session=session,
                candidate=candidate,
                idle_seconds=idle_seconds,
                curator_mode=curator_mode,
                inty_trace_id=inty_trace_id,
            )

    return _run_dreaming_batch_locked(
        session=session,
        candidate=candidate,
        idle_seconds=idle_seconds,
        curator_mode=curator_mode,
        inty_trace_id=inty_trace_id,
    )


def run_dreaming_batch_with_candidate(
    session: CompanionSession,
    *,
    candidate: DreamingCandidate,
    curator_mode: DreamingCuratorMode,
) -> DreamingBatchOutcome:
    """Run one dreaming batch from a caller-supplied candidate (eval force kick).

    Skips ``dreaming_due``, idle, inception policy, and UTC daily cap. The caller
    must supply a ``DreamingCandidate`` whose transcript boundary matches the store
    (no intervening rows since capture).
    """

    assert candidate is not None
    if not session.is_initialized:
        return DreamingBatchOutcome.NOT_DUE

    inty_trace_id = new_dreaming_batch_trace_id()

    if session.store.uses_repository_without_scope_disk:
        with try_dreaming_scope_advisory_lock(
            session.store.scope.registry_key()
        ) as lock_acquired:
            if not lock_acquired:
                record_dreaming_batch_observability(
                    session=session,
                    inty_trace_id=inty_trace_id,
                    outcome=DreamingBatchOutcome.ADVISORY_LOCK_BUSY,
                    candidate=candidate,
                    langsmith_root_run=None,
                )
                return DreamingBatchOutcome.ADVISORY_LOCK_BUSY
            return _run_dreaming_batch_locked(
                session=session,
                candidate=candidate,
                idle_seconds=1,
                curator_mode=curator_mode,
                inty_trace_id=inty_trace_id,
            )

    return _run_dreaming_batch_locked(
        session=session,
        candidate=candidate,
        idle_seconds=1,
        curator_mode=curator_mode,
        inty_trace_id=inty_trace_id,
    )


def _run_dreaming_batch_locked(
    *,
    session: CompanionSession,
    candidate: DreamingCandidate,
    idle_seconds: int,
    curator_mode: DreamingCuratorMode,
    inty_trace_id: str,
) -> DreamingBatchOutcome:
    _ = idle_seconds

    with dreaming_batch_langsmith_scope(
        session=session,
        inty_trace_id=inty_trace_id,
        candidate=candidate,
        parent_run_enabled=None,
    ) as (langsmith_root_run, langsmith_slice):
        try:

            def _complete_fn(messages: list[dict[str, Any]], role: str) -> str:
                return session.llm_client.complete_text(
                    messages,
                    model_role=role,
                    langsmith_extra=langsmith_slice.dreaming_consolidation_extra(
                        model_role=role
                    ),
                )

            consolidate_memory_during_dreaming(
                session.store,
                candidate.rows,
                curator_mode,
                _complete_fn,
                session.llm_client,
                langsmith_extra=langsmith_slice.dreaming_consolidation_extra(
                    model_role=DREAMING_ONE_SHOT_LLM_ROLE
                ),
                tool_bg_idle_event=session.tool_bg_idle,
            )
            assert_dreaming_transcript_boundary_unchanged(
                session.store, candidate
            )
            state = dreaming_state_from_candidate(
                candidate, processed_at=datetime.now(UTC)
            )
            save_dreaming_state(session.store, state)
        except BaseException as exc:
            record_dreaming_batch_observability(
                session=session,
                inty_trace_id=inty_trace_id,
                outcome=DreamingBatchOutcome.BATCH_FAILED,
                candidate=candidate,
                langsmith_root_run=langsmith_root_run,
                batch_error=repr(exc),
            )
            raise

    record_dreaming_batch_observability(
        session=session,
        inty_trace_id=inty_trace_id,
        outcome=DreamingBatchOutcome.CHECKPOINT_SAVED,
        candidate=candidate,
        langsmith_root_run=langsmith_root_run,
    )
    # TODO(dreaming-completion-notify): #3744 — signal per-scope in-process notifier
    # (threading.Event) so REPL regression can wait without Postgres MemDoc polling.
    return DreamingBatchOutcome.CHECKPOINT_SAVED
