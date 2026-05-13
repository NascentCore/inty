"""
Real LLM: companion run_turn must call memory_store_list_paths then answer.

Enable: INTY_COMPANION_HARNESS_REAL_LLM_TEST=1 and OPENROUTER_API_KEY.
Uses OpenRouter model nvidia/nemotron-3-super-120b-a12b:free.
Marked noci (skipped in default CI).
"""

from __future__ import annotations

import os
from typing import Any

import pytest

from app.core.companion_harness.companion.llm_client import CompanionLLMClient, CompanionLLMConfig
from app.core.companion_harness.companion.memory_pipeline import MemoryPipelineConfig
from app.core.companion_harness.companion.memory_store import MemoryStore
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.turn import run_turn

_OPENROUTER_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"


def _require_real_companion_harness_llm_test() -> None:
    if os.getenv("INTY_COMPANION_HARNESS_REAL_LLM_TEST") != "1":
        pytest.skip(
            "Set INTY_COMPANION_HARNESS_REAL_LLM_TEST=1 to run companion harness real LLM tests"
        )
    if not (os.getenv("OPENROUTER_API_KEY") or "").strip():
        pytest.skip("OPENROUTER_API_KEY is required for companion harness real LLM tests")


class _InstrumentedCompanionLLMClient(CompanionLLMClient):
    def __init__(self, config: CompanionLLMConfig) -> None:
        super().__init__(config)
        self.chat_rounds = 0
        self.saw_assistant_tool_calls = False

    def chat_completion(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str | None = None,
        tools: list[Any] | None = None,
        tool_choice: str | None = None,
        response_format: dict[str, Any] | None = None,
        scene: str | None = None,
    ) -> Any:
        self.chat_rounds += 1
        resp = super().chat_completion(
            messages=messages,
            model=model,
            tools=tools,
            tool_choice=tool_choice,
            response_format=response_format,
            scene=scene,
        )
        msg = resp.choices[0].message
        tcs = getattr(msg, "tool_calls", None) or []
        if tcs:
            self.saw_assistant_tool_calls = True
        return resp


@pytest.mark.noci
@pytest.mark.slow
@pytest.mark.asyncio
async def test_run_turn_real_llm_lists_scope_then_names_hello_file(tmp_path) -> None:
    _require_real_companion_harness_llm_test()

    root = tmp_path
    scope = CompanionScope("real-llm", "agent", root.name)
    store = MemoryStore(scope=scope, repository=None)
    store.write_document("IDENTITY.md", "# ID\nidentity doc")
    store.write_document("SOUL.md", "# SOUL\nsoul doc")
    store.write_document("USER.md", "# USER\nInitial profile.")
    store.write_document("MEMORY.md", "# MEM\nmemory doc")
    store.write_document("transcript.jsonl", "")
    store.write_document("context.json", "{}\n")
    store.write_document("hello.txt", "hi")

    cfg = CompanionLLMConfig(
        api_key=os.environ["OPENROUTER_API_KEY"].strip(),
        api_base=os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1"),
        default_model=_OPENROUTER_MODEL,
        chat_model=_OPENROUTER_MODEL,
        tool_model=_OPENROUTER_MODEL,
    )
    client = _InstrumentedCompanionLLMClient(cfg)

    mem_cfg = MemoryPipelineConfig(
        day_summary_disabled=True,
        user_update_disabled=True,
        soul_update_disabled=True,
    )
    user_prompt = (
        "You MUST call the memory_store_list_paths tool first with relative_path \"\" (empty string) "
        "to list the MemoryStore scope root. Do not guess. After you receive the tool output, reply in one "
        "short English sentence. That sentence MUST contain the exact substring hello.txt."
    )
    out = await run_turn(
        user_prompt,
        store=store,
        llm_client=client,
        defer_memory_update=True,
        memory_config=mem_cfg,
    )

    assert client.saw_assistant_tool_calls, "model never returned tool_calls"
    assert client.chat_rounds >= 2, "expected at least one tool round and one final reply"
    assert "hello.txt" in out.assistant_text.lower()
    tr = store.read_document("transcript.jsonl")
    assert "hello.txt" in tr.lower()
