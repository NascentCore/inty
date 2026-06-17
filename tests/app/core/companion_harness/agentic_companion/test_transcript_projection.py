"""Tests for transcript projection from queue records."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.agentic_companion.transcript_projection import (
    MemoryStoreTranscriptProjector,
)
from app.core.companion_harness.agentic_companion.types import (
    AgentOutputMessage,
    UserInputMessage,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)
from app.services.agentic_companion.downlink import DownlinkKind


@pytest.mark.asyncio
async def test_transcript_projection_includes_queue_ids() -> None:
    scope = AgentScope(user_id="u1", agent_id="a1")
    store = MemoryStore(scope=scope.to_companion_scope(), repository=None)
    projector = MemoryStoreTranscriptProjector()
    now = datetime.now(timezone.utc)
    await projector.project_input(
        store=store,
        record=UserInputMessage(
            message_id="in-1",
            scope=scope,
            channel=CompanionRuntimeChannel.TELEGRAM,
            wire_id="wire",
            text="hi",
            received_at_utc=now,
        ),
    )
    await projector.project_output(
        store=store,
        record=AgentOutputMessage(
            message_id="out-1",
            scope=scope,
            batch_id="batch-1",
            kind=DownlinkKind.USER_REPLY,
            text="hello",
            created_at_utc=now,
            message_ids=("in-1",),
        ),
    )
    body = store.read_document_if_exists(DEFAULT_MEMORY_STORE_SCOPE_PATHS.transcript)
    assert body is not None
    lines = [ln for ln in body.strip().split("\n") if ln]
    assert len(lines) == 2
    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert first["uuid"] == "in-1"
    assert first["queue_kind"] == "input"
    assert second["uuid"] == "out-1"
    assert second["queue_kind"] == "output"
