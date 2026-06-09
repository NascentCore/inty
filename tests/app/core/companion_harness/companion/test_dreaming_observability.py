from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.core.companion_harness.companion.dreaming import DreamingCandidate
from app.core.companion_harness.companion.dreaming_observability import (
    INNER_TICK_DREAMING_RUNTIME_EVENT_KIND,
    DreamingBatchOutcome,
    build_inner_tick_dreaming_runtime_event_record,
    record_dreaming_batch_observability,
)
from app.core.companion_harness.runtime.models import ChatMessage, InnerTickActivity
from app.core.companion_harness.companion.runtime_events import read_runtime_events
from app.core.companion_harness.runtime.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore


def _candidate() -> DreamingCandidate:
    now = datetime.now(timezone.utc)
    return DreamingCandidate(
        rows=[
            ChatMessage(
                role="user",
                content="hi",
                ts=now.isoformat(),
                uuid="u1",
            )
        ],
        latest_user_ts=now,
        boundary_line_count=1,
        boundary_uuid="u1",
    )


def _session(store: MemoryStore) -> MagicMock:
    session = MagicMock()
    session.user_id = "user-1"
    session.companion_id = "agent-1"
    session.chat_id = "chat-1"
    session.store = store
    return session


def test_build_inner_tick_dreaming_runtime_event_record_fields() -> None:
    store = MemoryStore(
        scope=CompanionScope("u", "a", "c"),
        repository=None,
    )
    session = _session(store)
    record = build_inner_tick_dreaming_runtime_event_record(
        session=session,
        inty_trace_id="trace-1",
        outcome=DreamingBatchOutcome.CHECKPOINT_SAVED,
        candidate=_candidate(),
        langsmith_trace_id="ls-trace",
        langsmith_run_id="ls-run",
    )
    assert record["kind"] == INNER_TICK_DREAMING_RUNTIME_EVENT_KIND
    assert record["inner_tick_activity"] == InnerTickActivity.DREAMING.value
    assert record["outcome"] == "checkpoint_saved"
    assert record["boundary_uuid"] == "u1"
    assert record["row_count"] == 1
    assert record["langsmith_trace_id"] == "ls-trace"


@patch(
    "app.core.companion_harness.companion.llm_chat_runtime.create_companion_turn_root_run",
    return_value=None,
)
def test_dreaming_batch_langsmith_scope_yields_none_when_parent_disabled(
    _create: MagicMock,
) -> None:
    from app.core.companion_harness.companion.dreaming_observability import (
        dreaming_batch_langsmith_scope,
    )

    session = MagicMock()
    session.user_id = "u"
    session.companion_id = "a"
    session.llm_client.resolve_model.return_value = MagicMock(
        id_on_provider="m/chat"
    )

    with dreaming_batch_langsmith_scope(
        session=session,
        inty_trace_id="t",
        candidate=_candidate(),
        parent_run_enabled=False,
    ) as root:
        assert root is None
