"""Tests for dual-LLM chat vs tool system-message stack helpers."""

from __future__ import annotations

from pathlib import Path

from app.core.companion_harness.companion.prompt_stack import (
    append_runtime_output_format_system_message,
)
from app.core.companion_harness.companion.prompts.system_messages import (
    build_system_messages_for_chat_track,
    build_system_messages_for_tool_track,
)
from app.core.companion_harness.companion.dual_llm_message_stacks import (
    dual_llm_system_message_variants,
    replace_leading_system_messages_multi,
)
from app.core.companion_harness.companion.models import ContextMeta, InnerTickActivity
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.prompting.bundle import PromptBundle
from app.utils.config import CompanionMemoryBootstrapType


def _bundle() -> PromptBundle:
    return PromptBundle(
        identity="identity\n",
        soul="soul\n",
        style_md="style\n",
        user_md="user\n",
        memory_md="memory\n",
    )


def test_replace_leading_system_messages_multi_swaps_prefix() -> None:
    messages = [
        {"role": "system", "content": "old-a"},
        {"role": "system", "content": "old-b"},
        {"role": "user", "content": "hi"},
    ]
    replaced = replace_leading_system_messages_multi(
        messages,
        [{"role": "system", "content": "new"}],
        stack_depth=2,
    )
    assert replaced == [
        {"role": "system", "content": "new"},
        {"role": "user", "content": "hi"},
    ]


def test_dual_llm_system_message_variants_maintenance_tool_differs_from_chat(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("dual-llm-stacks", "agent", tmp_path.name),
        repository=None,
    )
    runtime_context = TurnRuntimeContext(
        channel=CompanionRuntimeChannel.APP,
        implicit_signal_bundle=None,
    )
    tool_msgs, chat_msgs = dual_llm_system_message_variants(
        store=store,
        bundle=_bundle(),
        context=ContextMeta(),
        memory_bootstrap_type=CompanionMemoryBootstrapType.NONE.value,
        inner_tick_turn=True,
        route_inner_activity=InnerTickActivity.MAINTENANCE,
        runtime_context=runtime_context,
    )
    tool_text = "\n".join(
        str(m.get("content") or "") for m in tool_msgs if m.get("role") == "system"
    )
    chat_text = "\n".join(
        str(m.get("content") or "") for m in chat_msgs if m.get("role") == "system"
    )
    assert "用户当地时间" not in tool_text
    assert "用户当地时间" in chat_text


def test_dual_llm_system_message_variants_user_chat_matches_builders(
    tmp_path: Path,
) -> None:
    store = MemoryStore(
        scope=CompanionScope("dual-llm-stacks-user", "agent", tmp_path.name),
        repository=None,
    )
    bundle = _bundle()
    context = ContextMeta()
    runtime_context = TurnRuntimeContext(
        channel=CompanionRuntimeChannel.APP,
        implicit_signal_bundle=None,
    )
    memory_bootstrap_type = CompanionMemoryBootstrapType.NONE.value
    tool_msgs, chat_msgs = dual_llm_system_message_variants(
        store=store,
        bundle=bundle,
        context=context,
        memory_bootstrap_type=memory_bootstrap_type,
        inner_tick_turn=False,
        route_inner_activity=InnerTickActivity.MAINTENANCE,
        runtime_context=runtime_context,
    )
    expected_tool = append_runtime_output_format_system_message(
        system_messages=build_system_messages_for_tool_track(bundle, context),
        bundle=bundle,
        runtime_context=runtime_context,
    )
    expected_chat = append_runtime_output_format_system_message(
        system_messages=build_system_messages_for_chat_track(
            bundle,
            context,
            memory_bootstrap_type,
        ),
        bundle=bundle,
        runtime_context=runtime_context,
    )
    assert tool_msgs == expected_tool
    assert chat_msgs == expected_chat
