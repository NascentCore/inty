"""Bootstrap track must persist transcript.jsonl as user row(s) then assistant row(s)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.core.companion_harness.companion.proactive_chat import (
    ProactiveChatConfig,
    next_proactive_chat_wait_seconds,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.turn import (
    run_companion_user_chat_turn,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    CONTEXT_JSON_REL,
    TRANSCRIPT_JSONL_REL,
)
from app.external_services.fakes.openai import (
    FakeCompletionStep,
    fake_step_text,
    fake_step_tool_call,
)
from tests.app.core.companion_harness.companion.bootstrap_test_helpers import (
    bootstrap_queue_turn_deps,
)
from tests.app.core.companion_harness.companion.companion_scripted_llm import (
    companion_llm_client_with_scripted_transport,
    scripted_harness_llm_config,
)

_NEVER = 86400.0 * 365.0


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
    for rel in ("IDENTITY.md", "SOUL.md", "USER.md", "MEMORY.md"):
        store.write_document(rel, f"{rel}\n")
    store.write_document(TRANSCRIPT_JSONL_REL, "")


def _bootstrap_deps(
    store: MemoryStore,
    script: tuple[FakeCompletionStep, ...],
) -> Any:
    client, _fake = companion_llm_client_with_scripted_transport(
        scripted_harness_llm_config(),
        script,
    )
    return bootstrap_queue_turn_deps(store, client)


def _transcript_rows(store: MemoryStore) -> list[dict[str, Any]]:
    body = store.read_document(TRANSCRIPT_JSONL_REL)
    assert body is not None
    return [json.loads(line) for line in body.splitlines() if line.strip()]


@pytest.mark.asyncio
async def test_bootstrap_single_round_transcript_user_before_assistant(
    tmp_path: Path,
) -> None:
    scope = CompanionScope("bootstrap-tr-order", "agent", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    _seed_bootstrap_workspace(store)
    deps = _bootstrap_deps(store, (fake_step_text("还没有名字呢"),))

    out = await run_companion_user_chat_turn("你叫啥？", deps=deps)

    rows = _transcript_rows(store)
    assert [row["role"] for row in rows] == ["user", "assistant"]
    assert rows[0]["content"] == "你叫啥？"
    assert rows[0]["uuid"] == out.user_msg_uuid
    assert rows[1]["reply_to"] == out.user_msg_uuid
    assert rows[1]["content"] == "还没有名字呢"


@pytest.mark.asyncio
async def test_bootstrap_multi_round_transcript_user_before_all_assistants(
    tmp_path: Path,
) -> None:
    scope = CompanionScope("bootstrap-tr-multi", "agent", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    _seed_bootstrap_workspace(store)
    deps = _bootstrap_deps(
        store,
        (
            fake_step_tool_call(
                name="memory_store_write_document",
                arguments=json.dumps(
                    {
                        "relative_path": "IDENTITY.md",
                        "content": "孔明\n",
                    },
                    ensure_ascii=False,
                ),
                tool_call_id="tc-1",
                content="我先记一下",
            ),
            fake_step_text("从现在起我就是孔明"),
        ),
    )

    out = await run_companion_user_chat_turn("你就叫孔明吧", deps=deps)

    rows = _transcript_rows(store)
    assert [row["role"] for row in rows] == ["user", "assistant", "assistant"]
    assert rows[0]["uuid"] == out.user_msg_uuid
    assert rows[1]["reply_to"] == out.user_msg_uuid
    assert rows[2]["reply_to"] == out.user_msg_uuid
    assert rows[1]["content"] == "我先记一下"
    assert rows[2]["content"] == "从现在起我就是孔明"
    ready = await deps.agentic_output_queue.pull_ready_batch()
    assert [row.text for row in ready] == ["我先记一下", "从现在起我就是孔明"]


@pytest.mark.asyncio
async def test_bootstrap_transcript_tail_assistant_enables_proactive_scheduling(
    tmp_path: Path,
) -> None:
    scope = CompanionScope("bootstrap-tr-proactive", "agent", tmp_path.name)
    store = MemoryStore(scope=scope, repository=None)
    _seed_bootstrap_workspace(store)
    deps = _bootstrap_deps(store, (fake_step_text("reply"),))

    await run_companion_user_chat_turn("hello", deps=deps)

    cfg = ProactiveChatConfig(min_transcript_lines=2)
    assert next_proactive_chat_wait_seconds(store, cfg) != _NEVER
