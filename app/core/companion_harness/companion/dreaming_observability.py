"""Observability for sleeping-state dreaming batches (not a ``run_turn`` track).

``InnerTickActivity.DREAMING`` labels LangSmith parent runs and
``.companion_runtime_events.jsonl`` records. Dreaming does not produce
``CompanionTurnResult`` or REPL assistant metadata.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from enum import StrEnum
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from loguru import logger

from app.core.companion_harness.companion.dreaming import DreamingCandidate
from app.core.companion_harness.companion.langsmith_turn_slice import (
    CompanionTurnLangsmithSlice,
)
from app.core.companion_harness.companion.models import InnerTickActivity
from app.services.agentic_companion.langsmith_channel_resolve import (
    resolve_langsmith_slice_for_session,
)

if TYPE_CHECKING:
    from app.core.companion_harness.companion.manager import CompanionSession
from app.core.companion_harness.companion.runtime_events import (
    append_runtime_event,
)
from app.core.companion_harness.companion.utc import utc_iso_ts

INNER_TICK_DREAMING_RUNTIME_EVENT_KIND = "inner_tick_dreaming"


class DreamingBatchOutcome(StrEnum):
    """Result of one dreaming batch attempt under ``turn_lock``."""

    NOT_DUE = "not_due"
    CHECKPOINT_SAVED = "checkpoint_saved"
    BATCH_FAILED = "batch_failed"


def build_inner_tick_dreaming_runtime_event_record(
    *,
    session: CompanionSession,
    inty_trace_id: str,
    outcome: DreamingBatchOutcome,
    candidate: DreamingCandidate,
    langsmith_trace_id: str,
    langsmith_run_id: str,
) -> dict[str, Any]:
    """JSONL record for one dreaming batch (poll slot 4, no user-visible turn)."""
    return {
        "ts": utc_iso_ts(),
        "kind": INNER_TICK_DREAMING_RUNTIME_EVENT_KIND,
        "inner_tick_activity": InnerTickActivity.DREAMING.value,
        "user_id": session.user_id,
        "agent_id": session.companion_id,
        "chat_id": str(session.chat_id),
        "trace_id": inty_trace_id,
        "outcome": outcome.value,
        "boundary_uuid": candidate.boundary_uuid,
        "row_count": len(candidate.rows),
        "langsmith_trace_id": langsmith_trace_id,
        "langsmith_run_id": langsmith_run_id,
    }


@contextmanager
def dreaming_batch_langsmith_scope(
    *,
    session: CompanionSession,
    inty_trace_id: str,
    candidate: DreamingCandidate,
    parent_run_enabled: bool | None,
) -> Iterator[tuple[Any | None, CompanionTurnLangsmithSlice]]:
    """Open a LangSmith parent run for one dreaming memory batch."""
    from app.core.companion_harness.companion.llm_chat_runtime import (
        create_companion_turn_root_run,
    )

    langsmith_slice = resolve_langsmith_slice_for_session(session)
    chat_model = session.llm_client.resolve_model("chat")
    tool_model = session.llm_client.resolve_model("tool")
    root = create_companion_turn_root_run(
        inty_trace_id=inty_trace_id,
        user_msg_uuid=candidate.boundary_uuid,
        chat_model=chat_model,
        tool_model=tool_model,
        user_id=session.user_id,
        companion_id=session.companion_id,
        parent_run_enabled=parent_run_enabled,
        inner_tick_turn=True,
        inner_tick_activity=InnerTickActivity.DREAMING,
        transcript_newest_message_uuid=candidate.boundary_uuid,
        langsmith_slice=langsmith_slice,
    )
    if root is not None:
        from langsmith.run_helpers import tracing_context

        with tracing_context(parent=root):
            yield root, langsmith_slice
    else:
        yield None, langsmith_slice


def record_dreaming_batch_observability(
    *,
    session: CompanionSession,
    inty_trace_id: str,
    outcome: DreamingBatchOutcome,
    candidate: DreamingCandidate,
    langsmith_root_run: Any | None,
    batch_error: str | None = None,
) -> None:
    """Persist runtime event and close LangSmith parent for one dreaming batch."""
    assert batch_error is None or outcome == DreamingBatchOutcome.BATCH_FAILED
    from app.core.companion_harness.companion.llm_chat_runtime import (
        companion_turn_langsmith_parent_run_id_str,
        companion_turn_langsmith_parent_trace_id_str,
        end_companion_turn_root_run_safe,
    )

    ls_trace_id = companion_turn_langsmith_parent_trace_id_str(
        langsmith_root_run
    )
    ls_run_id = companion_turn_langsmith_parent_run_id_str(langsmith_root_run)
    append_runtime_event(
        session.store,
        build_inner_tick_dreaming_runtime_event_record(
            session=session,
            inty_trace_id=inty_trace_id,
            outcome=outcome,
            candidate=candidate,
            langsmith_trace_id=ls_trace_id,
            langsmith_run_id=ls_run_id,
        ),
    )
    if batch_error is not None:
        end_companion_turn_root_run_safe(
            langsmith_root_run,
            error=batch_error,
            ls_end_source="dreaming_batch_failed",
        )
    else:
        end_companion_turn_root_run_safe(
            langsmith_root_run,
            outputs={
                "inner_tick_activity": InnerTickActivity.DREAMING.value,
                "outcome": outcome.value,
                "row_count": len(candidate.rows),
                "boundary_uuid": candidate.boundary_uuid,
                "langsmith_trace_id": ls_trace_id,
                "langsmith_run_id": ls_run_id,
            },
            ls_end_source="dreaming_batch",
        )
    logger.info(
        "companion_dreaming batch_observed user={} agent={} chat={} outcome={} "
        "rows={} trace_id={} langsmith_trace_id={}",
        session.user_id,
        session.companion_id,
        session.chat_id,
        outcome.value,
        len(candidate.rows),
        inty_trace_id,
        ls_trace_id,
    )


def new_dreaming_batch_trace_id() -> str:
    """Fresh ``inty_trace_id`` for a dreaming batch (not a transcript user row)."""
    return str(uuid.uuid4())
