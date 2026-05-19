"""Reload companion system prefix after MemoryStore scope / context.json changes mid-turn."""

from __future__ import annotations

from typing import Any

from app.schemas.implicit_signals import ImplicitSignalBundle
from app.utils.config import CompanionMemoryBootstrapType

from .ai_private_prompt import get_ai_private_jsonl_text_for_prompt
from .bootstrap_user_interactive import interactive_bootstrap_active
from app.core.companion_harness.memory.memory_store import MemoryStore
from .models import (
    ContextMeta,
    InnerTickActivity,
    PromptBundle,
    load_context_meta,
    load_prompt_bundle,
)
from .implicit_signal_messages import implicit_user_signed_on_chat_turn
from .prompts.system_messages import build_system_messages
from app.core.companion_harness.tools.companion_tools import (
    build_companion_tools,
    build_openai_repl_tools_inner_tick,
)
from .turn_routes import TurnRouteMode, resolve_turn_route_mode


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
    store: MemoryStore,
    bundle: PromptBundle,
    context: ContextMeta,
    memory_bootstrap_type: str,
    inner_tick_turn: bool,
    inner_tick_activity: InnerTickActivity,
    tool_side_compact_system_prompt: bool,
    include_significance_perception_slice: bool | None = None,
    implicit_signal_bundle: ImplicitSignalBundle | None = None,
    implicit_user_signed_on_turn: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], TurnRouteMode]:
    """
    Single source for companion chat-round tools list and system message stack.

    Must stay aligned with ``turn.run_turn`` for the same explicit arguments. Callers that only
    build system-prefix variants for ``ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL`` pass
    ``implicit_user_signed_on_turn=False`` on purpose: implicit sign-on greetings strip tools
    earlier and never take that route (short greeting, no background tool loop).
    When ``tool_side_compact_system_prompt`` is True (background tool LLM stack), interactive
    bootstrap extra system blocks are omitted; tool availability still follows ``memory_bootstrap_type``
    and context.

    When ``implicit_user_signed_on_turn`` is True (and not an inner-tick turn), tools are
    omitted and system prompts skip tool contracts so the model does one chat completion only.
    """
    interactive_bootstrap = interactive_bootstrap_active(
        feature_enabled=(
            memory_bootstrap_type
            == CompanionMemoryBootstrapType.USER_INTERACTIVE.value
        ),
        meta=context,
    )
    tick_proactive = (
        inner_tick_turn and inner_tick_activity == InnerTickActivity.PROACTIVE_CHAT
    )
    ai_private_text = ""
    if inner_tick_turn and not tick_proactive:
        ai_private_text = get_ai_private_jsonl_text_for_prompt(store)
    route_inner_activity = (
        inner_tick_activity if inner_tick_turn else InnerTickActivity.MAINTENANCE
    )
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
    chat_only_implicit_sign_on = (
        implicit_user_signed_on_turn and not inner_tick_turn
    )
    if chat_only_implicit_sign_on:
        tools_for_turn = []
    # Compact system stack is only for the background tool LLM path; skip interactive-bootstrap
    # system blocks there (foreground chat stack still uses ``interactive_bootstrap``).
    system_prompt_interactive_bootstrap = (
        interactive_bootstrap if not tool_side_compact_system_prompt else False
    )
    route_mode = resolve_turn_route_mode(
        inner_tick_turn=inner_tick_turn,
        inner_tick_activity=route_inner_activity,
        tools_enabled=bool(tools_for_turn),
    )
    use_dual_structured_chat = (
        (not inner_tick_turn)
        and (not tools_for_turn)
        and route_mode != TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL
    )
    # When None: inject SIGNIFICANCE_PERCEPTION.md + dual-envelope output contract for the same
    # turns that use ``use_dual_structured_chat`` in run_turn, and for the *foreground* chat stack
    # in ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL (``_async_dual_llm_system_message_variants`` forces
    # include_significance_perception_slice=True on the chat side). Tells the model how to fill
    # importance_* fields in the JSON envelope; see ``dual_llm_chat_branch_envelope`` module docstring.
    resolved_sig = (
        include_significance_perception_slice
        if include_significance_perception_slice is not None
        else use_dual_structured_chat
    )
    if tool_side_compact_system_prompt:
        system_messages = build_system_messages(
            bundle,
            context,
            enable_tools=(not tick_proactive)
            and not chat_only_implicit_sign_on,
            enable_user_profile_tool=False,
            inner_tick_turn=inner_tick_turn,
            inner_tick_activity=route_inner_activity,
            ai_private_text=ai_private_text,
            tool_side_compact=True,
            interactive_bootstrap_active=system_prompt_interactive_bootstrap,
            include_significance_perception_slice=False,
            implicit_signal_bundle=implicit_signal_bundle,
        )
    else:
        # Foreground chat completion uses tools=None; mirrored contract + envelope slice
        # instead of the full "(6) companion_runtime_inspect" block (impossible without tools=).
        async_fg_chat = (
            route_mode == TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL
        )
        system_messages = build_system_messages(
            bundle,
            context,
            enable_tools=(not tick_proactive)
            and not chat_only_implicit_sign_on,
            inner_tick_turn=inner_tick_turn,
            inner_tick_activity=route_inner_activity,
            ai_private_text=ai_private_text,
            async_foreground_chat_stack=async_fg_chat,
            interactive_bootstrap_active=system_prompt_interactive_bootstrap,
            include_significance_perception_slice=resolved_sig,
            implicit_signal_bundle=implicit_signal_bundle,
        )
    return tools_for_turn, system_messages, route_mode


def refresh_companion_turn_prompt_stack(
    *,
    store: MemoryStore,
    memory_bootstrap_type: str,
    inner_tick_turn: bool,
    inner_tick_activity: InnerTickActivity,
    messages: list[dict[str, Any]],
    tool_side_compact_system_prompt: bool,
    implicit_signal_bundle: ImplicitSignalBundle | None = None,
) -> list[dict[str, Any]]:
    """
    Re-read context.json and prompt slices, replace leading system messages, return tools schema.
    """
    context = load_context_meta(store=store)
    bundle = load_prompt_bundle(store, meta=context)
    implicit_user_signed_on_turn = implicit_user_signed_on_chat_turn(
        implicit_signal_bundle=implicit_signal_bundle,
        inner_tick_turn=inner_tick_turn,
    )
    tools_for_turn, refreshed, _route_mode = (
        companion_turn_tools_and_system_messages(
            store=store,
            bundle=bundle,
            context=context,
            memory_bootstrap_type=memory_bootstrap_type,
            inner_tick_turn=inner_tick_turn,
            inner_tick_activity=inner_tick_activity,
            tool_side_compact_system_prompt=tool_side_compact_system_prompt,
            include_significance_perception_slice=None,
            implicit_signal_bundle=implicit_signal_bundle,
            implicit_user_signed_on_turn=implicit_user_signed_on_turn,
        )
    )
    replace_leading_system_messages_inplace(messages, refreshed)
    return tools_for_turn
