"""
Real LLM: companion user chat turn must call memory_store_list_paths then answer.

Enable: INTY_COMPANION_HARNESS_REAL_LLM_TEST=1 and OPENROUTER_API_KEY.
Uses OpenRouter model nvidia/nemotron-3-super-120b-a12b:free.
Marked noci (skipped in default CI).
"""

from __future__ import annotations

import os
from typing import Any

import pytest

from app.core.companion_harness.companion.llm_client import CompanionLLMClient, CompanionLLMConfig
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.turn import run_companion_user_chat_turn
from app.utils.config import CompanionMemoryBootstrapType
from app.utils.models_catalog import GenAIModel, resolve_chat_text_model

_OPENROUTER_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"


def _require_real_companion_harness_llm_test() -> None:
    if os.getenv("INTY_COMPANION_HARNESS_REAL_LLM_TEST") != "1":
        pytest.skip(
            "Set INTY_COMPANION_HARNESS_REAL_LLM_TEST=1 to run Companion Harness real LLM tests"
        )
    if not (os.getenv("OPENROUTER_API_KEY") or "").strip():
        pytest.skip("OPENROUTER_API_KEY is required for Companion Harness real LLM tests")


class _InstrumentedCompanionLLMClient(CompanionLLMClient):
    def __init__(self, config: CompanionLLMConfig) -> None:
        super().__init__(config)
        self.chat_rounds = 0
        self.saw_assistant_tool_calls = False

    def chat_completion(
        self,
        *,
        messages: list[dict[str, Any]],
        model: GenAIModel | None = None,
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
        default_model=resolve_chat_text_model(_OPENROUTER_MODEL),
        chat_model=resolve_chat_text_model(_OPENROUTER_MODEL),
        tool_model=resolve_chat_text_model(_OPENROUTER_MODEL),
    )
    client = _InstrumentedCompanionLLMClient(cfg)
    user_prompt = (
        "You MUST call the memory_store_list_paths tool first with relative_path \"\" (empty string) "
        "to list the MemoryStore scope root. Do not guess. After you receive the tool output, reply in one "
        "short English sentence. That sentence MUST contain the exact substring hello.txt."
    )
    out = await run_companion_user_chat_turn(
        user_prompt,
        store=store,
        llm_client=client,
        transcript_compaction=None,
        transcript_llm_window_max_messages=None,
        repository_only_store_text=False,
        memory_bootstrap_type=CompanionMemoryBootstrapType.NONE.value,
        background_output_sink=None,
        preset_user_msg_uuid=None,
        implicit_signal_bundle=None,
        langsmith_parent_run_enabled=None,
        tool_bg_idle_event=None,
    )

    assert client.saw_assistant_tool_calls, "model never returned tool_calls"
    assert client.chat_rounds >= 2, "expected at least one tool round and one final reply"
    assert "hello.txt" in out.assistant_text.lower()
    tr = store.read_document("transcript.jsonl")
    assert "hello.txt" in tr.lower()
