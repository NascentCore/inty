"""DreamingBatch orchestration: single entry for sleeping-state memory consolidation.

Generated entirely by Cursor agent for Phase 3.4 runtime seam slice.

``run_dreaming_batch_if_due`` is the only DreamingBatch orchestrator. Callers
(``companion_chat_service``, inner-tick fire) resolve ``CompanionSession`` and
hold ``turn_lock`` before calling here. See ``runtime`` package docstring for the
lock contract.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.companion_harness.companion.dreaming import (
    assert_dreaming_transcript_boundary_unchanged,
    dreaming_due,
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
    consolidate_memory_during_dreaming,
)


def run_dreaming_batch_if_due(
    session: CompanionSession,
    *,
    idle_seconds: int,
) -> DreamingBatchOutcome:
    """Run one sleeping-state dreaming batch when due.

    ``dreaming_due`` enforces idle time plus **at most one successful dream per UTC
    calendar day** per scope (intentional; see ``companion.dreaming``).

    Caller must hold scope ``CompanionSession.turn_lock`` (#3272). Re-checks ``dreaming_due`` inside the lock so conditions may change while waiting.
    Prototype: ``transcript.jsonl`` must not change during the batch; mismatch after
    ``consolidate_memory_during_dreaming`` raises ``DreamingTranscriptBoundaryMismatchError``
    (see ``companion.dreaming`` module doc — #3272, #3271, tool_bg timing TODO).
    TODO(dreaming-day-rollup): inner-tick merge may require boundary guard on
    ``transcript_inner_tick.jsonl`` too (#3376).

    TODO(dreaming-cluster-lock): Postgres advisory lock per scope when running multi-process
    backend — https://github.com/NascentCore/inty/issues/3271

    TODO(scope-inner-tick-worker): Callable from scope-level worker without WS/Weixin
    presence (#3255 — https://github.com/NascentCore/inty/issues/3255); caller holds scope
    ``turn_lock`` on ``CompanionSession`` instead.
    """
    assert idle_seconds > 0
    if not session.is_initialized:
        return DreamingBatchOutcome.NOT_DUE

    candidate = dreaming_due(
        session.store,
        now=datetime.now(timezone.utc),
        dreaming_idle_seconds=idle_seconds,
    )
    if candidate is None:
        return DreamingBatchOutcome.NOT_DUE

    inty_trace_id = new_dreaming_batch_trace_id()

    # TODO(dreaming-batch-langsmith-finally): On ``DreamingTranscriptBoundaryMismatchError`` (or
    # any batch failure inside ``dreaming_batch_langsmith_scope``), ``record_dreaming_batch_observability``
    # is skipped — LangSmith parent may not get ``end_companion_turn_root_run_safe``. Use try/finally
    # to always end the parent (failure outcome + optional runtime event) before re-raise.

    with dreaming_batch_langsmith_scope(
        session=session,
        inty_trace_id=inty_trace_id,
        candidate=candidate,
        parent_run_enabled=None,
    ) as (langsmith_root_run, langsmith_slice):

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
            _complete_fn,
            tool_bg_idle_event=session.tool_bg_idle,
        )
        assert_dreaming_transcript_boundary_unchanged(session.store, candidate)
        state = dreaming_state_from_candidate(
            candidate, processed_at=datetime.now(timezone.utc)
        )
        save_dreaming_state(session.store, state)

    record_dreaming_batch_observability(
        session=session,
        inty_trace_id=inty_trace_id,
        outcome=DreamingBatchOutcome.CHECKPOINT_SAVED,
        candidate=candidate,
        langsmith_root_run=langsmith_root_run,
    )
    return DreamingBatchOutcome.CHECKPOINT_SAVED
