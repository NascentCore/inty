from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.companion_harness.companion.ai_private_prompt import (
    append_ai_private_thought,
    load_ai_private_thoughts,
)
from app.core.companion_harness.companion.models import (
    AI_PRIVATE_SPLICE_MANIFEST_SOURCE,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.turn import (
    run_companion_user_chat_turn,
)
from tests.app.core.companion_harness.companion.bootstrap_test_helpers import (
    mark_interactive_bootstrap_completed,
    queue_serving_turn_deps,
)
from app.core.companion_harness.loop.config import UserTurnLlmLoopMode
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)
from tests.app.core.companion_harness.companion.companion_scripted_llm import (
    SettledUserChatScriptScenario,
    build_scripted_settled_user_chat_script,
    companion_llm_client_with_scripted_transport,
    scripted_harness_llm_config,
    with_scripted_user_turn_llm_loop_mode,
)


@pytest.mark.asyncio
async def test_successful_user_chat_persists_manifest_and_surfaces(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("manifest", "a", tmp_path.name),
        repository=None,
    )
    p = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    for rel in (
        p.identity,
        p.soul,
        p.style_md,
        p.user_md,
        p.memory_md,
        p.channels_md,
    ):
        store.write_document(rel, f"{rel}\n")
    store.write_document(p.context_json, '{"context_mode":"intimate"}\n')
    store.append_jsonl_record(
        p.transcript,
        {
            "role": "user",
            "content": "earlier",
            "ts": "2026-01-02T08:00:00+00:00",
            "uuid": "user-anchor",
        },
    )
    thought = append_ai_private_thought(
        store, text="monolog to splice", after_user_msg_uuid="user-anchor"
    )
    mark_interactive_bootstrap_completed(store)
    built = build_scripted_settled_user_chat_script(
        UserTurnLlmLoopMode.IN_TURN_SINGLE_LLM,
        SettledUserChatScriptScenario.NO_TOOLS,
    )
    client, _ = companion_llm_client_with_scripted_transport(
        scripted_harness_llm_config(),
        built.steps,
    )
    deps = queue_serving_turn_deps(store, client)
    with with_scripted_user_turn_llm_loop_mode(
        UserTurnLlmLoopMode.IN_TURN_SINGLE_LLM
    ):
        result = await run_companion_user_chat_turn("hello again", deps=deps)
    assert built.expected_foreground_reply is not None
    assert result.assistant_text == built.expected_foreground_reply
    assert load_ai_private_thoughts(store) == []
    body = store.read_document(p.transcript)
    lines = [json.loads(line) for line in body.strip().splitlines()]
    manifest_rows = [
        row
        for row in lines
        if row.get("source") == AI_PRIVATE_SPLICE_MANIFEST_SOURCE
    ]
    assert len(manifest_rows) == 1
    assert manifest_rows[0]["ai_private_thought_uuids"] == [thought.uuid]
    assert manifest_rows[-1]["source"] == AI_PRIVATE_SPLICE_MANIFEST_SOURCE
