"""Observability for sleeping-state dreaming batches (not a ``run_turn`` track).

``InnerTickActivity.DREAMING`` labels LangSmith parent runs and
``.companion_runtime_events.jsonl`` records. Dreaming does not produce
``CompanionTurnResult`` or REPL assistant metadata.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Iterator

from loguru import logger

from app.core.companion_harness.runtime.dreaming import DreamingCandidate
from app.core.companion_harness.runtime.models import InnerTickActivity

if TYPE_CHECKING:
    from app.core.companion_harness.runtime.manager import CompanionSession
from app.core.companion_harness.runtime.runtime_events import (
    append_runtime_event,
)
from app.core.companion_harness.runtime.utc import utc_iso_ts

INNER_TICK_DREAMING_RUNTIME_EVENT_KIND = "inner_tick_dreaming"


class DreamingBatchOutcome(StrEnum):
    """Result of one dreaming batch attempt under ``turn_lock``."""

    NOT_DUE = "not_due"
    CHECKPOINT_SAVED = "checkpoint_saved"


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
) -> Iterator[Any | None]:
    """Open a LangSmith parent run for one dreaming memory batch."""
    from app.core.companion_harness.runtime.llm_chat_runtime import (
        create_companion_turn_root_run,
    )

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
    )
    if root is not None:
        from langsmith.run_helpers import tracing_context

        with tracing_context(parent=root):
            yield root
    else:
        yield None


def record_dreaming_batch_observability(
    *,
    session: CompanionSession,
    inty_trace_id: str,
    outcome: DreamingBatchOutcome,
    candidate: DreamingCandidate,
    langsmith_root_run: Any | None,
) -> None:
    """Persist runtime event and close LangSmith parent for one dreaming batch.

    TODO(dreaming-batch-langsmith-finally): Callers that raise before this runs leave the parent
    open — see ``run_dreaming_batch_if_due``; end parent in try/finally on failure paths.
    """
    from app.core.companion_harness.runtime.llm_chat_runtime import (
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
