"""Tests for companion prompt stack assembly (tools list, system messages, refresh)."""

from __future__ import annotations

import json

from app.utils.config import CompanionMemoryBootstrapType

from app.core.companion_harness.companion.bootstrap_user_interactive import (
    tool_companion_bootstrap_user_interactive_complete,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.companion.models import (
    CompanionTurnTrack,
    InnerTickActivity,
    load_context_meta,
    load_prompt_bundle,
)
from app.core.companion_harness.companion.prompt_stack import (
    companion_turn_tools_and_system_messages,
    refresh_companion_turn_prompt_stack,
    replace_leading_system_messages_inplace,
)
from app.core.companion_harness.companion.prompts.system_messages import (
    build_system_messages,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.tools.companion_tools import build_openai_repl_tools_inner_tick
from app.core.companion_harness.companion.turn_routes import TurnRouteMode
from app.schemas.implicit_signals import ImplicitSignalBundle


def _scope(tmp_path_name: str, suffix: str = "") -> CompanionScope:
    chat_id = f"{tmp_path_name}{suffix}"
    return CompanionScope("prompt-stack", "agent", chat_id)


def _seed_workspace_bootstrap_incomplete(scope: CompanionScope) -> MemoryStore:
    st = MemoryStore(scope=scope, repository=None)
    for rel, body in (
        ("IDENTITY.md", "id\n"),
        ("SOUL.md", "soul\n"),
        ("USER.md", "user\n"),
        ("MEMORY.md", "mem\n"),
    ):
        st.write_document(rel, body)
    st.write_document(
        "context.json",
        json.dumps(
            {
                "context_mode": "bootstrap",
                "user_id": "u",
                "companion_id": "a",
                "chat_id": "c",
                "workspace_bootstrap_user_interactive_completed": False,
            },
            ensure_ascii=False,
        )
        + "\n",
    )
    return st


def _joined_leading_system_contents(system_messages: list[dict]) -> str:
    parts: list[str] = []
    for m in system_messages:
        if m.get("role") != "system":
            break
        parts.append(str(m.get("content") or ""))
    return "\n".join(parts)


def test_inner_tick_loads_ai_private_jsonl_into_system(tmp_path) -> None:
    scope = _scope(tmp_path.name, "-tick")
    st = MemoryStore(scope=scope, repository=None)
    for rel, body in (
        ("IDENTITY.md", "id\n"),
        ("SOUL.md", "soul\n"),
        ("USER.md", "user\n"),
        ("MEMORY.md", "mem\n"),
    ):
        st.write_document(rel, body)
    st.write_document(
        "context.json",
        json.dumps(
            {
                "context_mode": "public",
                "user_id": "u",
                "companion_id": "a",
                "chat_id": "c",
            },
            ensure_ascii=False,
        )
        + "\n",
    )
    st.write_document("ai_private.jsonl", '{"text": "jl seed line"}\n')
    context = load_context_meta(store=st)
    bundle = load_prompt_bundle(st, meta=context)
    _, systems, _ = companion_turn_tools_and_system_messages(
        store=st,
        bundle=bundle,
        context=context,
        memory_bootstrap_type=CompanionMemoryBootstrapType.NONE.value,
        track=CompanionTurnTrack.INNER_TICK_MAINTENANCE,
    )
    joined = "\n".join(
        str(m.get("content") or "") for m in systems if m.get("role") == "system"
    )
    assert "jl seed line" in joined


def _seed_minimal_companion_workspace(scope: CompanionScope) -> MemoryStore:
    st = MemoryStore(scope=scope, repository=None)
    for rel, body in (
        ("IDENTITY.md", "id\n"),
        ("SOUL.md", "soul\n"),
        ("USER.md", "user\n"),
        ("MEMORY.md", "mem\n"),
    ):
        st.write_document(rel, body)
    st.write_document(
        "context.json",
        json.dumps(
            {
                "context_mode": "public",
                "user_id": "u",
                "companion_id": "a",
                "chat_id": "c",
            },
            ensure_ascii=False,
        )
        + "\n",
    )
    return st


def test_refresh_inner_tick_keeps_inner_tick_tools(tmp_path) -> None:
    scope = _scope(tmp_path.name, "-refresh-it")
    st = _seed_minimal_companion_workspace(scope)
    context = load_context_meta(store=st)
    bundle = load_prompt_bundle(st, meta=context)
    tools_before, systems, _ = companion_turn_tools_and_system_messages(
        store=st,
        bundle=bundle,
        context=context,
        memory_bootstrap_type=CompanionMemoryBootstrapType.NONE.value,
        track=CompanionTurnTrack.INNER_TICK_MAINTENANCE,
    )
    expected_names = {t["function"]["name"] for t in build_openai_repl_tools_inner_tick()}
    assert {t["function"]["name"] for t in tools_before} == expected_names

    messages = [dict(m) for m in systems]
    messages.append({"role": "user", "content": "tick"})
    new_tools = refresh_companion_turn_prompt_stack(
        store=st,
        memory_bootstrap_type=CompanionMemoryBootstrapType.NONE.value,
        inner_tick_turn=True,
        inner_tick_activity=InnerTickActivity.MAINTENANCE,
        messages=messages,
        track=CompanionTurnTrack.INNER_TICK_MAINTENANCE,
    )
    assert {t["function"]["name"] for t in new_tools} == expected_names

def test_async_foreground_chat_turn_resolves_async_route(tmp_path) -> None:
    scope = _scope(tmp_path.name, "-async-fg")
    st = _seed_minimal_companion_workspace(scope)
    context = load_context_meta(store=st)
    bundle = load_prompt_bundle(st, meta=context)
    _, systems, route = companion_turn_tools_and_system_messages(
        store=st,
        bundle=bundle,
        context=context,
        memory_bootstrap_type=CompanionMemoryBootstrapType.NONE.value,
        track=CompanionTurnTrack.USER_CHAT,
    )
    assert route == TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL
    assert "Dual-LLM chat branch" in _joined_leading_system_contents(systems)

def test_implicit_user_signed_on_chat_turn_forces_chat_only_route_and_no_tools(
    tmp_path,
) -> None:
    scope = _scope(tmp_path.name, "-implicit-sign")
    st = _seed_minimal_companion_workspace(scope)
    context = load_context_meta(store=st)
    bundle = load_prompt_bundle(st, meta=context)
    bundle_sig = ImplicitSignalBundle(user_signed_on=True)

    tools_normal, _, route_normal = companion_turn_tools_and_system_messages(
        store=st,
        bundle=bundle,
        context=context,
        memory_bootstrap_type=CompanionMemoryBootstrapType.NONE.value,
        track=CompanionTurnTrack.USER_CHAT,
    )
    tools_implicit, _, route_implicit = companion_turn_tools_and_system_messages(
        store=st,
        bundle=bundle,
        context=context,
        memory_bootstrap_type=CompanionMemoryBootstrapType.NONE.value,
        track=CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING,
    )
    assert len(tools_normal) > 0
    assert route_normal == TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL
    assert tools_implicit == []
    assert route_implicit == TurnRouteMode.CHAT_ONLY_SYNC

def test_implicit_user_signed_on_turn_does_not_strip_tools_for_inner_tick(
    tmp_path,
) -> None:
    scope = _scope(tmp_path.name, "-it-implicit")
    st = _seed_minimal_companion_workspace(scope)
    context = load_context_meta(store=st)
    bundle = load_prompt_bundle(st, meta=context)
    tools, _, route = companion_turn_tools_and_system_messages(
        store=st,
        bundle=bundle,
        context=context,
        memory_bootstrap_type=CompanionMemoryBootstrapType.NONE.value,
        track=CompanionTurnTrack.INNER_TICK_MAINTENANCE,
    )
    assert len(tools) > 0
    assert route == TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL

def test_refresh_implicit_user_signed_on_returns_empty_tools(tmp_path) -> None:
    scope = _scope(tmp_path.name, "-refresh-implicit")
    st = _seed_minimal_companion_workspace(scope)
    context = load_context_meta(store=st)
    bundle = load_prompt_bundle(st, meta=context)
    systems = build_system_messages(
        bundle,
        context,
        enable_tools=True,
        inner_tick_turn=False,
    )
    messages = [dict(m) for m in systems]
    messages.append({"role": "user", "content": "hello"})
    sig = ImplicitSignalBundle(user_signed_on=True)
    new_tools = refresh_companion_turn_prompt_stack(
        store=st,
        memory_bootstrap_type=CompanionMemoryBootstrapType.NONE.value,
        inner_tick_turn=False,
        inner_tick_activity=InnerTickActivity.MAINTENANCE,
        messages=messages,
        implicit_signal_bundle=sig,
        track=CompanionTurnTrack.USER_CHAT,
    )
    assert new_tools == []

def test_replace_leading_system_messages_inplace_keeps_tail() -> None:
    msgs = [
        {"role": "system", "content": "a"},
        {"role": "system", "content": "b"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "yo"},
    ]
    replace_leading_system_messages_inplace(
        msgs, [{"role": "system", "content": "fresh"}]
    )
    assert msgs == [
        {"role": "system", "content": "fresh"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "yo"},
    ]


def test_implicit_sign_on_greeting_injects_bootstrap_when_incomplete(tmp_path) -> None:
    scope = _scope(tmp_path.name, "-greet-boot")
    st = _seed_workspace_bootstrap_incomplete(scope)
    context = load_context_meta(store=st)
    bundle = load_prompt_bundle(st, meta=context)
    mb = CompanionMemoryBootstrapType.USER_INTERACTIVE.value
    tools, systems, route = companion_turn_tools_and_system_messages(
        store=st,
        bundle=bundle,
        context=context,
        memory_bootstrap_type=mb,
        track=CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING,
    )
    joined = _joined_leading_system_contents(systems)
    assert tools == []
    assert route == TurnRouteMode.CHAT_ONLY_SYNC
    assert "Agentic 初始化执行规范" in joined
    assert "companion_bootstrap_user_interactive_complete" in joined


def test_user_chat_track_omits_bootstrap_blocks_even_when_incomplete(tmp_path) -> None:
    scope = _scope(tmp_path.name, "-no-boot-in-chat")
    st = _seed_workspace_bootstrap_incomplete(scope)
    context = load_context_meta(store=st)
    bundle = load_prompt_bundle(st, meta=context)
    mb = CompanionMemoryBootstrapType.USER_INTERACTIVE.value
    _, systems, _ = companion_turn_tools_and_system_messages(
        store=st,
        bundle=bundle,
        context=context,
        memory_bootstrap_type=mb,
        track=CompanionTurnTrack.USER_CHAT,
    )
    joined = _joined_leading_system_contents(systems)
    assert "Agentic 初始化执行规范" not in joined


def test_refresh_drops_interactive_bootstrap_after_complete(tmp_path) -> None:
    scope = _scope(tmp_path.name, "-drop-boot")
    st = _seed_workspace_bootstrap_incomplete(scope)
    context = load_context_meta(store=st)
    bundle = load_prompt_bundle(st, meta=context)
    systems = build_system_messages(
        bundle,
        context,
        enable_tools=True,
        inner_tick_turn=False,
        interactive_bootstrap_active=True,
    )
    messages = [dict(m) for m in systems]
    messages.append({"role": "user", "content": "hello"})

    before = _joined_leading_system_contents(messages)
    assert "Agentic 初始化执行规范" in before

    out = tool_companion_bootstrap_user_interactive_complete(st, note=None)
    assert out.startswith("OK ")
    assert json.loads(st.read_document("context.json"))[
        "workspace_bootstrap_user_interactive_completed"
    ] is True

    new_tools = refresh_companion_turn_prompt_stack(
        store=st,
        memory_bootstrap_type=CompanionMemoryBootstrapType.USER_INTERACTIVE.value,
        inner_tick_turn=False,
        inner_tick_activity=InnerTickActivity.MAINTENANCE,
        messages=messages,
        track=CompanionTurnTrack.USER_CHAT,
    )

    after = _joined_leading_system_contents(messages)
    assert "Agentic 初始化执行规范" not in after
    assert "BOOTSTRAP.md" not in after
    tool_names = [t["function"]["name"] for t in new_tools]
    assert "memory_store_write_document" in tool_names
    assert "companion_bootstrap_user_interactive_complete" not in tool_names

    assert messages[-1] == {"role": "user", "content": "hello"}
