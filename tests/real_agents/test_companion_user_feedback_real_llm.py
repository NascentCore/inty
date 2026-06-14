"""
Real LLM: model must call companion_record_user_feedback on user complaint.

Enable: INTY_COMPANION_HARNESS_REAL_LLM_TEST=1 and OPENROUTER_API_KEY.
Uses in-process tool loop (not tool_background) to avoid pytest loop shutdown races.
Marked noci (skipped in default CI).
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Any

import pytest

from app.core.companion_harness.companion.llm_client import CompanionLLMClient, CompanionLLMConfig
from app.core.companion_harness.companion.llm_runtime_events import (
    LlmRuntimeEventBind,
    companion_llm_runtime_event_bind_ctx,
)
from app.core.companion_harness.companion.message_format import openai_assistant_message_dict
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.tools.companion_tool_definitions import (
    CompanionToolName,
    openai_tools_for_names,
)
from app.core.companion_harness.tools.companion_tool_runtime import execute_tool_call
from app.core.companion_harness.tools.companion_user_feedback import (
    COMPANION_RECORD_USER_FEEDBACK_TOOL_NAME,
    USER_FEEDBACK_JSONL_REL,
)
from app.core.companion_harness.tools.runtime import (
    resolve_openai_tool_call_loop_async,
)
from app.utils.models_catalog import resolve_chat_text_model

_OPENROUTER_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"


def _require_real_companion_harness_llm_test() -> None:
    if os.getenv("INTY_COMPANION_HARNESS_REAL_LLM_TEST") != "1":
        pytest.skip(
            "Set INTY_COMPANION_HARNESS_REAL_LLM_TEST=1 to run Companion Harness real LLM tests"
        )
    if not (os.getenv("OPENROUTER_API_KEY") or "").strip():
        pytest.skip("OPENROUTER_API_KEY is required for Companion Harness real LLM tests")


@pytest.mark.noci
@pytest.mark.slow
@pytest.mark.asyncio
async def test_real_llm_calls_companion_record_user_feedback(tmp_path) -> None:
    _require_real_companion_harness_llm_test()

    rid = uuid.uuid4().hex[:8]
    scope = CompanionScope(f"u-rlm-{rid}", f"c-rlm-{rid}", f"chat-rlm-{rid}")
    store = MemoryStore(scope=scope, repository=None)
    store.write_document("context.json", '{"context_mode":"intimate"}\n')
    store.write_document("transcript.jsonl", "")
    store.write_document("USER.md", "# USER\n")

    cfg = CompanionLLMConfig(
        api_key=os.environ["OPENROUTER_API_KEY"].strip(),
        api_base=os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1"),
        default_model=resolve_chat_text_model(_OPENROUTER_MODEL),
        chat_model=resolve_chat_text_model(_OPENROUTER_MODEL),
        tool_model=resolve_chat_text_model(_OPENROUTER_MODEL),
    )
    client = CompanionLLMClient(cfg)
    tools = openai_tools_for_names(
        (CompanionToolName.COMPANION_RECORD_USER_FEEDBACK,),
        description_overrides={},
    )
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are Inty. When the user complains about your behavior, memory, or tone, "
                "you MUST call companion_record_user_feedback before replying."
            ),
        },
        {
            "role": "user",
            "content": (
                "I'm frustrated — you keep forgetting my timezone (US/Pacific). "
                "File my complaint with companion_record_user_feedback now."
            ),
        },
    ]

    bind = LlmRuntimeEventBind(
        memory_store=store,
        trace_id=f"trace-rlm-{rid}",
        user_msg_uuid=f"msg-rlm-{rid}",
        phase="tool_background",
        scene=None,
    )
    token = companion_llm_runtime_event_bind_ctx.set(bind)
    saw_feedback_tool = False

    try:
        initial = client.chat_completion(
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

        async def _execute_tool(name: str, raw_arguments: str) -> tuple[str, str | None]:
            nonlocal saw_feedback_tool
            if name == COMPANION_RECORD_USER_FEEDBACK_TOOL_NAME:
                saw_feedback_tool = True
            out = await execute_tool_call(store, name, raw_arguments)
            return out, None

        async def _continue_chat(
            msgs: list[dict[str, Any]],
        ) -> tuple[Any, str | None]:
            resp = client.chat_completion(messages=msgs, tools=tools)
            return resp, None

        await resolve_openai_tool_call_loop_async(
            response=initial,
            openai_messages=messages,
            max_tool_call_rounds=4,
            execute_tool_call=_execute_tool,
            continue_chat=_continue_chat,
            build_assistant_tool_call_message=openai_assistant_message_dict,
            insert_system_message=lambda msgs, text: msgs.insert(
                max(len(msgs) - 1, 0),
                {"role": "system", "content": text},
            ),
        )
    finally:
        companion_llm_runtime_event_bind_ctx.reset(token)

    assert saw_feedback_tool, (
        f"real LLM did not call {COMPANION_RECORD_USER_FEEDBACK_TOOL_NAME}"
    )
    feedback_raw = store.read_document_if_exists(USER_FEEDBACK_JSONL_REL)
    assert feedback_raw
    row = json.loads(feedback_raw.strip().split("\n")[0])
    assert row["kind"] == "snapshot"
    assert row["complaint_summary"].strip()
    assert row["correlation"]["user_msg_uuid"] == f"msg-rlm-{rid}"
