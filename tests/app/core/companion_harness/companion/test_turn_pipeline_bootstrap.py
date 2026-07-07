"""Tests for bootstrap ``USER_CHAT_BOOTSTRAP`` prompt plan assembly in turn_pipeline."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from app.core.companion_harness.companion.models import CompanionTurnTrack
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.turn_pipeline import (
    build_companion_turn_prompt_plan,
    load_companion_turn_state,
)
from app.core.companion_harness.companion.turn_tail_user import (
    TurnTailUserMessage,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    CONTEXT_JSON_REL,
    TRANSCRIPT_JSONL_REL,
)
from app.core.companion_harness.memory.memory_store_scope import (
    ensure_minimal_documents_in_store,
)
from app.core.companion_harness.prompt_builder import PromptBuilder
from app.core.companion_harness.tools.companion_tool_runtime import (
    build_openai_bootstrap_track_tools,
)


def _seed_bootstrap_workspace(store: MemoryStore) -> None:
    store.write_document(
        CONTEXT_JSON_REL,
        json.dumps(
            {
                "context_mode": "unspecific",
                "user_id": "u",
                "companion_id": "a",
                "chat_id": "c",
                "workspace_bootstrap_user_interactive_completed": False,
            },
            ensure_ascii=False,
        )
        + "\n",
    )
    ensure_minimal_documents_in_store(store)
    store.write_document(TRANSCRIPT_JSONL_REL, "")


def _tail_user() -> tuple[TurnTailUserMessage, ...]:
    return (
        TurnTailUserMessage(
            message_id="user-1",
            text="hello",
            received_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
        ),
    )


def test_bootstrap_prompt_plan_system_messages_match_prompt_builder(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("pipeline-bootstrap", "agent", tmp_path.name),
        repository=None,
    )
    _seed_bootstrap_workspace(store)
    runtime_context = TurnRuntimeContext(
        channel=ChannelKind.APP_WS,
        implicit_signal_bundle=None,
    )
    loaded_state = load_companion_turn_state(
        store=store,
        track=CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
        transcript_llm_window_max_messages=None,
    )
    plan = build_companion_turn_prompt_plan(
        store=store,
        loaded_state=loaded_state,
        tail_user_messages=_tail_user(),
        track=CompanionTurnTrack.USER_CHAT_BOOTSTRAP,
        tick_proactive=False,
        implicit_sign_on_turn=False,
        runtime_context=runtime_context,
        transcript_compaction=None,
        tail_splice_thoughts=[],
    )
    expected_system = PromptBuilder(
        bundle=loaded_state.bundle,
        context=loaded_state.context,
        runtime_context=runtime_context,
    ).bootstrap_turn_system_dicts()
    assert plan.system_messages == expected_system
    assert plan.tools_for_turn == build_openai_bootstrap_track_tools()
