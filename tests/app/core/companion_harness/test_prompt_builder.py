"""Tests for single-LLM ``PromptBuilder`` and ``PromptPlan``."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.core.companion_harness.companion.bootstrap import (
    load_bootstrap_telegram_profile_slice_text,
)
from app.core.companion_harness.companion.models import ChatMessage, ContextMeta
from app.core.companion_harness.companion.prompts.system_messages import (
    build_system_messages,
    build_system_messages_for_bootstrap_track,
    build_system_messages_for_tool_track,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.turn_tail_user import (
    TurnTailUserMessage,
)
from app.core.companion_harness.memory.user_md_identity import (
    UserIdentityFieldLabel,
    fill_user_md_identity_fields,
    load_user_md_template_text,
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
    build_openai_bootstrap_track_tools,
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


def _telegram_bootstrap_builder(*, user_md: str) -> PromptBuilder:
    return PromptBuilder(
        bundle=PromptBundle(
            identity="identity",
            soul="soul",
            user_md=user_md,
            memory_md="",
        ),
        context=ContextMeta(
            workspace_bootstrap_user_interactive_completed=False,
            profile_collection_required=True,
        ),
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.TELEGRAM,
            implicit_signal_bundle=None,
        ),
    )


def _bootstrap_tail_user() -> tuple[TurnTailUserMessage, ...]:
    return (
        TurnTailUserMessage(
            message_id="user-1",
            text="hello",
            received_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
        ),
    )


def test_bootstrap_user_chat_prompt_injects_telegram_profile_slice() -> None:
    user_md = load_user_md_template_text()
    builder = _telegram_bootstrap_builder(user_md=user_md)
    plan = builder.build_bootstrap_user_chat_prompt(
        transcript_window=[],
        tail_user_messages=_bootstrap_tail_user(),
        tools=tuple(build_openai_bootstrap_track_tools()),
        implicit_sign_on_turn=False,
        tail_splice_thoughts=(),
    )
    system_text = _system_text(plan.messages)
    assert load_bootstrap_telegram_profile_slice_text() in system_text
    assert "仍待自然了解" in system_text


def test_bootstrap_user_chat_prompt_omits_profile_slice_without_flag() -> None:
    builder = PromptBuilder(
        bundle=PromptBundle(
            identity="identity",
            soul="soul",
            user_md=load_user_md_template_text(),
            memory_md="",
        ),
        context=ContextMeta(
            workspace_bootstrap_user_interactive_completed=False,
        ),
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.TELEGRAM,
            implicit_signal_bundle=None,
        ),
    )
    plan = builder.build_bootstrap_user_chat_prompt(
        transcript_window=[],
        tail_user_messages=_bootstrap_tail_user(),
        tools=tuple(build_openai_bootstrap_track_tools()),
        implicit_sign_on_turn=False,
        tail_splice_thoughts=(),
    )
    system_text = _system_text(plan.messages)
    assert load_bootstrap_telegram_profile_slice_text() not in system_text


def test_bootstrap_user_chat_prompt_omits_profile_slice_on_app_ws() -> None:
    builder = PromptBuilder(
        bundle=PromptBundle(
            identity="identity",
            soul="soul",
            user_md=load_user_md_template_text(),
            memory_md="",
        ),
        context=ContextMeta(
            workspace_bootstrap_user_interactive_completed=False,
            profile_collection_required=True,
        ),
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        ),
    )
    plan = builder.build_bootstrap_user_chat_prompt(
        transcript_window=[],
        tail_user_messages=_bootstrap_tail_user(),
        tools=tuple(build_openai_bootstrap_track_tools()),
        implicit_sign_on_turn=False,
        tail_splice_thoughts=(),
    )
    system_text = _system_text(plan.messages)
    assert load_bootstrap_telegram_profile_slice_text() not in system_text


def test_build_user_chat_prompt_unchanged_no_cohort_overlay() -> None:
    builder = PromptBuilder(
        bundle=_bundle(),
        context=ContextMeta(profile_collection_required=True),
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.TELEGRAM,
            implicit_signal_bundle=None,
        ),
    )
    plan = builder.build_user_chat_prompt(
        transcript_window=[],
        tail_user_messages=_bootstrap_tail_user(),
        tools=(),
        implicit_sign_on_turn=False,
        tail_splice_thoughts=(),
    )
    system_text = _system_text(plan.messages)
    assert load_bootstrap_telegram_profile_slice_text() not in system_text
    assert "仍待自然了解" not in system_text


def test_refresh_bootstrap_prefix_injects_telegram_profile_slice() -> None:
    store = MemoryStore(
        scope=CompanionScope("user-boot", "agent-boot", "chat-boot"),
        repository=None,
    )
    store.write_document(
        "context.json",
        json.dumps(
            {
                "context_mode": "bootstrap",
                "profile_collection_required": True,
                "workspace_bootstrap_user_interactive_completed": False,
            }
        ),
    )
    store.write_document("IDENTITY.md", "id")
    store.write_document("USER.md", load_user_md_template_text())
    runtime = TurnRuntimeContext(
        channel=ChannelKind.TELEGRAM,
        implicit_signal_bundle=None,
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": "stale"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "", "tool_calls": []},
        {"role": "tool", "content": "{}", "tool_call_id": "call-1"},
    ]
    refresh_single_llm_bootstrap_chat_prompt_prefix(
        store=store,
        messages=messages,
        runtime_context=runtime,
    )
    system_text = "\n".join(
        str(m.get("content") or "")
        for m in messages
        if m.get("role") == "system"
    )
    assert load_bootstrap_telegram_profile_slice_text() in system_text
    assert "仍待自然了解" in system_text


def test_refresh_bootstrap_prefix_updates_probe_hint_after_partial_user_md() -> (
    None
):
    partial_user_md = fill_user_md_identity_fields(
        load_user_md_template_text(),
        {UserIdentityFieldLabel.GENDER: "男"},
    )
    store = MemoryStore(
        scope=CompanionScope("user-boot", "agent-boot", "chat-boot"),
        repository=None,
    )
    store.write_document(
        "context.json",
        json.dumps(
            {
                "context_mode": "bootstrap",
                "profile_collection_required": True,
                "workspace_bootstrap_user_interactive_completed": False,
            }
        ),
    )
    store.write_document("IDENTITY.md", "id")
    store.write_document("USER.md", partial_user_md)
    runtime = TurnRuntimeContext(
        channel=ChannelKind.TELEGRAM,
        implicit_signal_bundle=None,
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": "stale"},
        {"role": "user", "content": "hi"},
    ]
    refresh_single_llm_bootstrap_chat_prompt_prefix(
        store=store,
        messages=messages,
        runtime_context=runtime,
    )
    system_text = "\n".join(
        str(m.get("content") or "")
        for m in messages
        if m.get("role") == "system"
    )
    hint_lines = [
        line for line in system_text.splitlines() if "仍待自然了解" in line
    ]
    assert len(hint_lines) == 1
    hint = hint_lines[0]
    assert UserIdentityFieldLabel.GENDER not in hint
    assert UserIdentityFieldLabel.AGE in hint
    assert UserIdentityFieldLabel.LOCATION in hint


def test_refresh_bootstrap_prefix_omits_cohort_after_bootstrap_complete() -> (
    None
):
    store = MemoryStore(
        scope=CompanionScope("user-boot", "agent-boot", "chat-boot"),
        repository=None,
    )
    store.write_document(
        "context.json",
        json.dumps(
            {
                "context_mode": "bootstrap",
                "profile_collection_required": True,
                "workspace_bootstrap_user_interactive_completed": True,
            }
        ),
    )
    store.write_document("IDENTITY.md", "id")
    store.write_document("USER.md", load_user_md_template_text())
    runtime = TurnRuntimeContext(
        channel=ChannelKind.TELEGRAM,
        implicit_signal_bundle=None,
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": "stale"},
        {"role": "user", "content": "hi"},
    ]
    refresh_single_llm_bootstrap_chat_prompt_prefix(
        store=store,
        messages=messages,
        runtime_context=runtime,
    )
    system_text = "\n".join(
        str(m.get("content") or "")
        for m in messages
        if m.get("role") == "system"
    )
    assert load_bootstrap_telegram_profile_slice_text() not in system_text
    assert "仍待自然了解" not in system_text


def test_prompt_builder_bootstrap_cohort_slices_match_legacy_track() -> None:
    user_md = load_user_md_template_text()
    context = ContextMeta(
        workspace_bootstrap_user_interactive_completed=False,
        profile_collection_required=True,
    )
    bundle = PromptBundle(
        identity="identity",
        soul="soul",
        user_md=user_md,
        memory_md="",
    )
    legacy_system = "\n".join(
        str(m.get("content") or "")
        for m in build_system_messages_for_bootstrap_track(
            bundle,
            context,
            ChannelKind.TELEGRAM,
        )
    )
    builder = _telegram_bootstrap_builder(user_md=user_md)
    plan = builder.build_bootstrap_user_chat_prompt(
        transcript_window=[],
        tail_user_messages=_bootstrap_tail_user(),
        tools=tuple(build_openai_bootstrap_track_tools()),
        implicit_sign_on_turn=False,
        tail_splice_thoughts=(),
    )
    prompt_builder_system = _system_text(plan.messages)
    telegram_slice = load_bootstrap_telegram_profile_slice_text()
    assert telegram_slice in legacy_system
    assert telegram_slice in prompt_builder_system
    assert "仍待自然了解" in legacy_system
    assert "仍待自然了解" in prompt_builder_system


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
                received_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
            ),
            TurnTailUserMessage(
                message_id="user-2",
                text="second",
                received_at_utc=datetime(2026, 1, 1, 0, 1, tzinfo=UTC),
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


def _dual_llm_base_messages() -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": "doctrine"},
        {"role": "system", "content": "persona"},
        {"role": "user", "content": "earlier"},
        {"role": "assistant", "content": "ok"},
        {"role": "system", "content": "## User's Local Time Context"},
        {"role": "user", "content": "complaint turn"},
    ]


def test_build_settled_user_chat_dual_llm_tool_prompt_plan_includes_disclosure_clause(
    monkeypatch,
) -> None:
    from app.core.companion_harness.tools import companion_user_feedback as mod

    monkeypatch.setattr(
        mod,
        "resolve_user_feedback_disclosure_mode",
        lambda: mod.UserFeedbackDisclosureMode.VISIBLE,
    )
    builder = PromptBuilder(
        bundle=_bundle(),
        context=ContextMeta(),
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        ),
    )
    tools = tuple(build_openai_repl_tools())
    plan = builder.build_settled_user_chat_dual_llm_tool_prompt_plan(
        base_messages=_dual_llm_base_messages(),
        stack_depth=2,
        tools=tools,
    )
    system_text = _system_text(plan.messages)
    assert "companion_record_user_feedback" in system_text
    assert "github_issue_url" in system_text
    assert plan.tools == tools


def test_build_settled_user_chat_dual_llm_tool_prompt_plan_omits_disclosure_when_hidden(
    monkeypatch,
) -> None:
    from app.core.companion_harness.tools import companion_user_feedback as mod

    monkeypatch.setattr(
        mod,
        "resolve_user_feedback_disclosure_mode",
        lambda: mod.UserFeedbackDisclosureMode.HIDDEN,
    )
    builder = PromptBuilder(
        bundle=_bundle(),
        context=ContextMeta(),
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        ),
    )
    plan = builder.build_settled_user_chat_dual_llm_tool_prompt_plan(
        base_messages=_dual_llm_base_messages(),
        stack_depth=2,
        tools=tuple(build_openai_repl_tools()),
    )
    system_text = _system_text(plan.messages)
    assert "github_issue_url" not in system_text
