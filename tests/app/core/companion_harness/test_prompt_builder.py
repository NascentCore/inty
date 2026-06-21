"""Tests for single-LLM ``PromptBuilder`` and ``PromptPlan``."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.companion_harness.companion.models import ChatMessage, ContextMeta
from app.core.companion_harness.companion.prompts.system_messages import (
    build_system_messages,
    build_system_messages_for_tool_track,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.turn_tail_user import (
    TurnTailUserMessage,
)
from app.core.companion_harness.prompt_builder import (
    PromptBuilder,
    PromptMessage,
    PromptMessageRole,
    openai_dialogue_dicts_to_prompt_messages,
    prompt_messages_to_openai_dicts,
    refresh_single_llm_bootstrap_chat_prompt_prefix,
    refresh_single_llm_user_chat_prompt_prefix,
)
from app.core.companion_harness.prompting.bundle import PromptBundle
from app.core.companion_harness.tools.companion_tool_runtime import (
    build_openai_repl_tools,
)
from app.core.companion_harness.tools.companion_tool_definitions import (
    CompanionToolName,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.memory.memory_store import MemoryStore


def _bundle() -> PromptBundle:
    return PromptBundle(
        identity="identity",
        soul="soul",
        user_md="user",
        memory_md="",
        tools_md="# Tools\ngenerate_image rules",
    )


def _system_text(plan_messages: tuple[PromptMessage, ...]) -> str:
    return "\n".join(
        message.content
        for message in plan_messages
        if message.role == PromptMessageRole.SYSTEM
    )


def test_build_user_chat_prompt_allows_tools_and_sets_tool_choice_none() -> (
    None
):
    tools = tuple(build_openai_repl_tools())
    builder = PromptBuilder(
        bundle=_bundle(),
        context=ContextMeta(),
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        ),
    )
    plan = builder.build_user_chat_prompt(
        transcript_window=[
            ChatMessage(
                role="user",
                content="hello",
                ts="2026-01-01T00:00:00+00:00",
            )
        ],
        tail_user_messages=(
            TurnTailUserMessage(
                message_id="user-1",
                text="画夜空",
                received_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
            ),
        ),
        tools=tools,
        implicit_sign_on_turn=False,
        tail_splice_thoughts=(),
    )
    assert plan.tool_choice is None
    assert plan.tools == tools
    joined = _system_text(plan.messages)
    assert "generate_image" in joined
    assert "本路 API 不带工具" not in joined
    assert "禁止在本路发起任何 tool_calls" not in joined
    assert "并行 chat 路已承担对用户话术" not in joined
    assert any("hello" in message.content for message in plan.messages)
    assert plan.messages[-1].role == PromptMessageRole.USER
    assert "画夜空" in plan.messages[-1].content


def test_build_user_chat_prompt_preserves_multi_user_tail() -> None:
    builder = PromptBuilder(
        bundle=_bundle(),
        context=ContextMeta(),
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        ),
    )
    plan = builder.build_user_chat_prompt(
        transcript_window=[],
        tail_user_messages=(
            TurnTailUserMessage(
                message_id="user-1",
                text="first",
                received_at_utc=datetime(2026, 1, 1, tzinfo=timezone.utc),
            ),
            TurnTailUserMessage(
                message_id="user-2",
                text="second",
                received_at_utc=datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc),
            ),
        ),
        tools=(),
        implicit_sign_on_turn=False,
        tail_splice_thoughts=(),
    )

    assert [message.role for message in plan.messages[-2:]] == [
        PromptMessageRole.USER,
        PromptMessageRole.USER,
    ]
    assert "first" in plan.messages[-2].content
    assert "second" in plan.messages[-1].content


def test_single_llm_user_chat_system_messages_differ_from_dual_foreground() -> (
    None
):
    bundle = _bundle()
    context = ContextMeta()
    dual_foreground = "\n".join(
        str(m.get("content") or "")
        for m in build_system_messages(
            bundle,
            context,
            enable_tools=True,
            async_foreground_chat_stack=True,
        )
    )
    single_llm = "\n".join(
        str(m.get("content") or "")
        for m in PromptBuilder(
            bundle=bundle,
            context=context,
            runtime_context=TurnRuntimeContext(
                channel=ChannelKind.APP_WS,
                implicit_signal_bundle=None,
            ),
        ).settled_single_llm_system_messages()
    )
    assert "禁止在本路发起任何 tool_calls" in dual_foreground
    assert "禁止在本路发起任何 tool_calls" not in single_llm


def test_prompt_messages_to_openai_dicts_boundary() -> None:
    messages = (
        PromptMessage(role=PromptMessageRole.SYSTEM, content="sys"),
        PromptMessage(role=PromptMessageRole.USER, content="hi"),
    )
    wire = prompt_messages_to_openai_dicts(messages)
    assert wire == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
    ]


def test_refresh_single_llm_user_chat_prompt_prefix_avoids_tool_background_compact() -> (
    None
):
    store = MemoryStore(
        scope=CompanionScope("user-1", "agent-1", "chat-1"),
        repository=None,
    )
    store.write_document(
        "context.json", '{"context_mode":"emotional_companion"}'
    )
    store.write_document("IDENTITY.md", "id")
    store.write_document("USER.md", "user")
    runtime = TurnRuntimeContext(
        channel=ChannelKind.APP_WS,
        implicit_signal_bundle=None,
    )
    compact_prefix = build_system_messages_for_tool_track(
        _bundle(),
        ContextMeta(),
    )
    compact_joined = "\n".join(
        str(m.get("content") or "") for m in compact_prefix
    )
    assert "并行 chat 路已承担对用户话术" in compact_joined

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": "stale"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "ok", "tool_calls": []},
        {"role": "tool", "content": "{}", "tool_call_id": "call-1"},
    ]
    refreshed_messages = refresh_single_llm_user_chat_prompt_prefix(
        store=store,
        messages=messages,
        runtime_context=runtime,
    )
    assert refreshed_messages is not messages
    assert any(
        tool["function"]["name"] == "generate_image"
        for tool in refreshed_messages
    )
    refreshed_joined = "\n".join(
        str(m.get("content") or "")
        for m in messages
        if m.get("role") == "system"
    )
    assert "并行 chat 路已承担对用户话术" not in refreshed_joined
    assert messages[-1]["role"] == "tool"


def test_refresh_single_llm_bootstrap_prompt_prefix_returns_bootstrap_tools() -> (
    None
):
    store = MemoryStore(
        scope=CompanionScope("user-boot", "agent-boot", "chat-boot"),
        repository=None,
    )
    store.write_document("context.json", '{"context_mode":"bootstrap"}')
    store.write_document("IDENTITY.md", "id")
    store.write_document("USER.md", "user")
    runtime = TurnRuntimeContext(
        channel=ChannelKind.APP_WS,
        implicit_signal_bundle=None,
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": "stale"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "", "tool_calls": []},
        {"role": "tool", "content": "{}", "tool_call_id": "call-1"},
    ]

    refreshed_tools = refresh_single_llm_bootstrap_chat_prompt_prefix(
        store=store,
        messages=messages,
        runtime_context=runtime,
    )

    assert any(
        tool["function"]["name"]
        == CompanionToolName.COMPANION_BOOTSTRAP_USER_INTERACTIVE_COMPLETE.value
        for tool in refreshed_tools
    )
    assert messages[0]["content"] != "stale"
    assert messages[-1]["role"] == "tool"


def test_openai_dialogue_dicts_to_prompt_messages() -> None:
    converted = openai_dialogue_dicts_to_prompt_messages(
        [
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"},
        ]
    )
    assert converted[0].role == PromptMessageRole.USER
    assert converted[1].role == PromptMessageRole.ASSISTANT
