"""Reload companion system prefix after workspace / context.json changes mid-turn."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.schemas.implicit_signals import ImplicitSignalBundle
from app.utils.config import CompanionWorkspaceBootstrapType

from .bootstrap_user_interactive import interactive_bootstrap_active
from .memory_store import MemoryStore
from .models import ContextMeta, InnerTickMode, PromptBundle, load_context_meta, load_prompt_bundle
from .prompts import build_system_messages
from .tools import build_companion_tools, build_openai_repl_tools_inner_tick
from .turn_routes import TurnRouteMode, resolve_turn_route_mode
from .workspace import WorkspacePaths


def replace_leading_system_messages_inplace(
    messages: list[dict[str, Any]],
    system_messages: list[dict[str, Any]],
) -> None:
    i = 0
    while i < len(messages) and messages[i].get("role") == "system":
        i += 1
    messages[:] = [*system_messages, *messages[i:]]


def companion_turn_tools_and_system_messages(
    *,
    bundle: PromptBundle,
    context: ContextMeta,
    workspace_bootstrap_type: str,
    inner_tick_turn: bool,
    inner_tick_mode: InnerTickMode,
    enable_async_tool_background: bool,
    tool_side_compact_system_prompt: bool,
    include_significance_perception_slice: bool | None = None,
    implicit_signal_bundle: ImplicitSignalBundle | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], TurnRouteMode]:
    """
    Single source for companion chat-round tools list and system message stack.

    Must stay aligned with ``turn.run_turn`` message assembly (same inputs -> same outputs).
    """
    interactive_bootstrap = interactive_bootstrap_active(
        feature_enabled=(
            workspace_bootstrap_type
            == CompanionWorkspaceBootstrapType.USER_INTERACTIVE.value
        ),
        meta=context,
    )
    tick_proactive = (
        inner_tick_turn and inner_tick_mode == InnerTickMode.PROACTIVE_CHAT
    )
    route_inner_mode = inner_tick_mode if inner_tick_turn else InnerTickMode.MAINTENANCE
    tools_for_turn: list[dict[str, Any]] = (
        []
        if tick_proactive
        else (
            build_openai_repl_tools_inner_tick()
            if inner_tick_turn
            else build_companion_tools(
                interactive_bootstrap_active=interactive_bootstrap
            )
        )
    )
    route_mode = resolve_turn_route_mode(
        inner_tick_turn=inner_tick_turn,
        inner_tick_mode=route_inner_mode,
        tools_enabled=bool(tools_for_turn),
        enable_async_tool_background=enable_async_tool_background,
    )
    use_dual_structured_chat = (
        (not inner_tick_turn)
        and (not tools_for_turn)
        and route_mode != TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL
    )
    resolved_sig = (
        include_significance_perception_slice
        if include_significance_perception_slice is not None
        else use_dual_structured_chat
    )
    if tool_side_compact_system_prompt:
        system_messages = build_system_messages(
            bundle,
            context,
            enable_tools=True,
            enable_user_profile_tool=False,
            inner_tick_turn=False,
            include_repl_image_generation_contract=True,
            tool_side_compact=True,
            interactive_bootstrap_active=interactive_bootstrap,
            include_significance_perception_slice=False,
            implicit_signal_bundle=implicit_signal_bundle,
        )
    else:
        system_messages = build_system_messages(
            bundle,
            context,
            enable_tools=not tick_proactive,
            inner_tick_turn=inner_tick_turn,
            inner_tick_mode=route_inner_mode,
            interactive_bootstrap_active=interactive_bootstrap,
            include_significance_perception_slice=resolved_sig,
            implicit_signal_bundle=implicit_signal_bundle,
        )
    return tools_for_turn, system_messages, route_mode


def refresh_companion_turn_prompt_stack(
    *,
    workspace: Path,
    store: MemoryStore,
    workspace_bootstrap_type: str,
    inner_tick_turn: bool,
    inner_tick_mode: InnerTickMode,
    enable_async_tool_background: bool,
    messages: list[dict[str, Any]],
    tool_side_compact_system_prompt: bool,
    implicit_signal_bundle: ImplicitSignalBundle | None = None,
) -> list[dict[str, Any]]:
    """
    Re-read context.json and prompt slices, replace leading system messages, return tools schema.
    """
    root = workspace.resolve()
    paths = WorkspacePaths(root=root)
    context = load_context_meta(paths.context_json, store=store)
    bundle = load_prompt_bundle(paths, store, meta=context)
    tools_for_turn, refreshed, _route_mode = companion_turn_tools_and_system_messages(
        bundle=bundle,
        context=context,
        workspace_bootstrap_type=workspace_bootstrap_type,
        inner_tick_turn=inner_tick_turn,
        inner_tick_mode=inner_tick_mode,
        enable_async_tool_background=enable_async_tool_background,
        tool_side_compact_system_prompt=tool_side_compact_system_prompt,
        include_significance_perception_slice=None,
        implicit_signal_bundle=implicit_signal_bundle,
    )
    replace_leading_system_messages_inplace(messages, refreshed)
    return tools_for_turn
