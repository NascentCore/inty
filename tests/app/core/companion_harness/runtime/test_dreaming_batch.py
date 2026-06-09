from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.core.companion_harness.companion.dreaming import (
    DreamingCandidate,
    DreamingTranscriptBoundaryMismatchError,
)
from app.core.companion_harness.companion.dreaming_observability import (
    DreamingBatchOutcome,
)
from app.core.companion_harness.companion.models import ChatMessage
from app.core.companion_harness.runtime.dreaming_batch import (
    run_dreaming_batch_if_due,
)


def _dreaming_candidate() -> DreamingCandidate:
    now = datetime.now(timezone.utc)
    return DreamingCandidate(
        rows=[
            ChatMessage(
                role="user",
                content="hi",
                ts=now.isoformat(),
                uuid="u",
            )
        ],
        latest_user_ts=now,
        boundary_line_count=1,
        boundary_uuid="u",
    )


def _session() -> MagicMock:
    session = MagicMock()
    session.is_initialized = True
    session.user_id = "u"
    session.companion_id = "a"
    session.chat_id = "c"
    session.store = MagicMock()
    session.llm_client = MagicMock()
    session.tool_bg_idle = MagicMock()
    return session


@contextmanager
def _noop_dreaming_observability(**_kwargs):
    yield None


def test_run_dreaming_batch_if_due_skips_when_not_due() -> None:
    session = _session()

    with (
        patch(
            "app.core.companion_harness.runtime.dreaming_batch.dreaming_due",
            return_value=None,
        ) as dreaming_due,
        patch(
            "app.core.companion_harness.runtime.dreaming_batch.consolidate_memory_during_dreaming"
        ) as memory_update,
    ):
        result = run_dreaming_batch_if_due(
            session,
            idle_seconds=120,
        )

    assert result == DreamingBatchOutcome.NOT_DUE
    dreaming_due.assert_called_once()
    memory_update.assert_not_called()


def test_run_dreaming_batch_if_due_skips_when_session_not_initialized() -> None:
    session = _session()
    session.is_initialized = False

    with patch(
        "app.core.companion_harness.runtime.dreaming_batch.dreaming_due",
    ) as dreaming_due:
        result = run_dreaming_batch_if_due(
            session,
            idle_seconds=120,
        )

    assert result == DreamingBatchOutcome.NOT_DUE
    dreaming_due.assert_not_called()


def test_run_dreaming_batch_if_due_raises_on_boundary_mismatch() -> None:
    session = _session()

    with (
        patch(
            "app.core.companion_harness.runtime.dreaming_batch.dreaming_due",
            return_value=_dreaming_candidate(),
        ),
        patch(
            "app.core.companion_harness.runtime.dreaming_batch.dreaming_batch_langsmith_scope",
            _noop_dreaming_observability,
        ),
        patch(
            "app.core.companion_harness.runtime.dreaming_batch.record_dreaming_batch_observability"
        ) as record_obs,
        patch(
            "app.core.companion_harness.runtime.dreaming_batch.consolidate_memory_during_dreaming"
        ) as memory_update,
        patch(
            "app.core.companion_harness.runtime.dreaming_batch.assert_dreaming_transcript_boundary_unchanged",
            side_effect=DreamingTranscriptBoundaryMismatchError("mismatch"),
        ),
        patch(
            "app.core.companion_harness.runtime.dreaming_batch.save_dreaming_state"
        ) as save_dreaming_state,
    ):
        with pytest.raises(DreamingTranscriptBoundaryMismatchError):
            run_dreaming_batch_if_due(
                session,
                idle_seconds=120,
            )

    memory_update.assert_called_once()
    save_dreaming_state.assert_not_called()
    record_obs.assert_not_called()


def test_run_dreaming_batch_if_due_saves_checkpoint_after_update() -> None:
    session = _session()

    with (
        patch(
            "app.core.companion_harness.runtime.dreaming_batch.dreaming_due",
            return_value=_dreaming_candidate(),
        ),
        patch(
            "app.core.companion_harness.runtime.dreaming_batch.dreaming_batch_langsmith_scope",
            _noop_dreaming_observability,
        ),
        patch(
            "app.core.companion_harness.runtime.dreaming_batch.record_dreaming_batch_observability"
        ) as record_obs,
        patch(
            "app.core.companion_harness.runtime.dreaming_batch.consolidate_memory_during_dreaming"
        ) as memory_update,
        patch(
            "app.core.companion_harness.runtime.dreaming_batch.assert_dreaming_transcript_boundary_unchanged",
        ),
        patch(
            "app.core.companion_harness.runtime.dreaming_batch.save_dreaming_state"
        ) as save_dreaming_state,
    ):
        result = run_dreaming_batch_if_due(
            session,
            idle_seconds=120,
        )

    assert result == DreamingBatchOutcome.CHECKPOINT_SAVED
    memory_update.assert_called_once()
    save_dreaming_state.assert_called_once()
    record_obs.assert_called_once()
