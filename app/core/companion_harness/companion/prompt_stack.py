"""Select and refresh the companion prompt stack for each turn track.

The companion turn track is the public routing fact: it decides which tool
schemas are exposed, which system-message wrapper is used, and which route mode
must be enforced.  Mid-turn refreshes re-read MemoryStore and ``context.json`` so
tool-side writes to persona/context documents become visible before the next
model leg continues.
"""

from __future__ import annotations

from typing import Any

from app.utils.config import CompanionMemoryBootstrapType

from app.core.companion_harness.companion.bootstrap import (
    interactive_bootstrap_active,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.prompting.bundle import PromptBundle
from .models import (
    CompanionTurnTrack,
    ContextMeta,
    InnerTickActivity,
    load_context_meta,
    load_prompt_bundle,
)
from .turn_track import turn_flags_for_track
from .implicit_signal_messages import implicit_user_signed_on_chat_turn
from .runtime_channel import CompanionRuntimeChannel, TurnRuntimeContext
from .prompts.system_messages import (
    build_system_messages_for_bootstrap_track,
    build_system_messages_for_chat_track,
    build_system_messages_for_implicit_sign_on_greeting,
    build_system_messages_for_inner_tick_maintenance,
    build_system_messages_for_inner_tick_proactive_chat,
    build_system_messages_for_inner_tick_scheduled,
    build_system_messages_for_tool_track,
    weixin_clawbot_contact_alias_system_message,
)
from app.core.companion_harness.tools.companion_tools import (
    build_companion_tools,
    build_openai_bootstrap_track_tools,
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


def output_format_prompt_slice_for_runtime_channel(
    *,
    bundle: PromptBundle,
    runtime_channel: CompanionRuntimeChannel,
) -> str:
    """Resolve channel output-format text from the runtime communication medium."""
    match runtime_channel:
        case CompanionRuntimeChannel.WECHAT_WEIXIN:
            return bundle.output_format_wechat_weixin_md
        case CompanionRuntimeChannel.APP:
            return ""


def append_runtime_output_format_system_message(
    *,
    system_messages: list[dict[str, Any]],
    bundle: PromptBundle,
    runtime_context: TurnRuntimeContext,
) -> list[dict[str, Any]]:
    """Append channel output-format prompt selected from runtime context."""
    output_format = output_format_prompt_slice_for_runtime_channel(
        bundle=bundle,
        runtime_channel=runtime_context.channel,
    )
    if output_format.strip():
        return [
            *system_messages,
            {"role": "system", "content": output_format.strip()},
        ]
    return system_messages


def companion_tools_for_turn(
    *,
    track: CompanionTurnTrack,
    inner_tick_turn: bool,
    inner_tick_activity: InnerTickActivity,
    implicit_user_signed_on_turn: bool = False,
) -> list[dict[str, Any]]:
    """OpenAI tool schemas for this turn (independent of which system-message wrapper runs)."""
    match track:
        case CompanionTurnTrack.USER_CHAT_BOOTSTRAP:
            tools_for_turn = build_openai_bootstrap_track_tools()
        case CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING:
            tools_for_turn = []
        case _:
            tick_proactive = (
                inner_tick_turn
                and inner_tick_activity == InnerTickActivity.PROACTIVE_CHAT
            )
            tools_for_turn = (
                []
                if tick_proactive
                else (
                    build_openai_repl_tools_inner_tick()
                    if inner_tick_turn
                    else build_companion_tools(
                        interactive_bootstrap_active=False
                    )
                )
            )
            if implicit_user_signed_on_turn and not inner_tick_turn:
                tools_for_turn = []
    return tools_for_turn


def companion_system_messages_for_track(
    *,
    store: MemoryStore,
    bundle: PromptBundle,
    context: ContextMeta,
    memory_bootstrap_type: str,
    track: CompanionTurnTrack,
    route_mode: TurnRouteMode,
    runtime_context: TurnRuntimeContext,
) -> list[dict[str, Any]]:
    """Pick the scenario wrapper from ``CompanionTurnTrack`` (see ``system_messages`` docstring)."""
    match track:
        case CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING:
            out = build_system_messages_for_implicit_sign_on_greeting(
                bundle,
                context,
                memory_bootstrap_type,
            )
        case CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT:
            out = build_system_messages_for_inner_tick_proactive_chat(
                bundle, context
            )
        case CompanionTurnTrack.INNER_TICK_SCHEDULED:
            out = build_system_messages_for_inner_tick_scheduled(
                bundle, context
            )
        case CompanionTurnTrack.INNER_TICK_MAINTENANCE:
            if (
                route_mode
                != TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL
            ):
                raise RuntimeError(
                    "inner_tick_maintenance track requires ASYNC route, got "
                    f"{route_mode.value}"
                )
            out = build_system_messages_for_inner_tick_maintenance(
                bundle, context, store
            )
        case CompanionTurnTrack.USER_CHAT_BOOTSTRAP:
            out = build_system_messages_for_bootstrap_track(bundle, context)
        case CompanionTurnTrack.USER_CHAT:
            if (
                route_mode
                != TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL
            ):
                raise RuntimeError(
                    "user_chat track requires ASYNC route, got "
                    f"{route_mode.value}"
                )
            out = build_system_messages_for_chat_track(
                bundle,
                context,
                memory_bootstrap_type,
            )
    out = append_runtime_output_format_system_message(
        system_messages=out,
        bundle=bundle,
        runtime_context=runtime_context,
    )
    if runtime_context.channel == CompanionRuntimeChannel.WECHAT_WEIXIN:
        out.append(weixin_clawbot_contact_alias_system_message())
    return out


def companion_turn_tools_and_system_messages(
    *,
    store: MemoryStore,
    bundle: PromptBundle,
    context: ContextMeta,
    memory_bootstrap_type: str,
    track: CompanionTurnTrack,
    implicit_user_signed_on_turn: bool = False,
    runtime_context: TurnRuntimeContext = TurnRuntimeContext(
        channel=CompanionRuntimeChannel.APP,
        implicit_signal_bundle=None,
    ),
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], TurnRouteMode]:
    """
    Single source for companion chat-round tools list and system message stack.

    ``USER_CHAT_BOOTSTRAP`` runs one in-turn tool loop so setup can write prompt
    slices before completion.  Normal user chat and maintenance inner tick require
    the async foreground/tool-background route.  Proactive, scheduled, and
    implicit sign-on greeting tracks are chat-only system stacks with no tools.
    """
    inner_tick_turn, route_inner_activity = turn_flags_for_track(track)
    if track == CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING:
        implicit_user_signed_on_turn = True
    tools_for_turn = companion_tools_for_turn(
        track=track,
        inner_tick_turn=inner_tick_turn,
        inner_tick_activity=route_inner_activity,
        implicit_user_signed_on_turn=implicit_user_signed_on_turn,
    )
    route_mode = resolve_turn_route_mode(
        inner_tick_turn=inner_tick_turn,
        inner_tick_activity=route_inner_activity,
        tools_enabled=bool(tools_for_turn),
    )
    system_messages = companion_system_messages_for_track(
        store=store,
        bundle=bundle,
        context=context,
        memory_bootstrap_type=memory_bootstrap_type,
        track=track,
        route_mode=route_mode,
        runtime_context=runtime_context,
    )
    return tools_for_turn, system_messages, route_mode


def refresh_companion_turn_prompt_stack(
    *,
    store: MemoryStore,
    memory_bootstrap_type: str,
    inner_tick_turn: bool,
    inner_tick_activity: InnerTickActivity,
    messages: list[dict[str, Any]],
    track: CompanionTurnTrack,
    runtime_context: TurnRuntimeContext = TurnRuntimeContext(
        channel=CompanionRuntimeChannel.APP,
        implicit_signal_bundle=None,
    ),
) -> list[dict[str, Any]]:
    """
    Re-read context.json and prompt slices, replace leading system messages, return tools schema.

    Only tool-capable tracks refresh here.  Chat-only tracks have no follow-up
    tool leg after their initial completion, so refreshing them would hide a
    routing bug rather than update useful context.
    """
    context = load_context_meta(store=store)
    bundle = load_prompt_bundle(store, meta=context)
    implicit_user_signed_on_turn = implicit_user_signed_on_chat_turn(
        implicit_signal_bundle=runtime_context.implicit_signal_bundle,
        inner_tick_turn=inner_tick_turn,
    )
    tools_for_turn = companion_tools_for_turn(
        track=track,
        inner_tick_turn=inner_tick_turn,
        inner_tick_activity=inner_tick_activity,
        implicit_user_signed_on_turn=implicit_user_signed_on_turn,
    )
    match track:
        case CompanionTurnTrack.USER_CHAT_BOOTSTRAP:
            bootstrap_still_active = interactive_bootstrap_active(
                feature_enabled=(
                    memory_bootstrap_type
                    == CompanionMemoryBootstrapType.USER_INTERACTIVE.value
                ),
                meta=context,
            )
            if bootstrap_still_active:
                refreshed = build_system_messages_for_bootstrap_track(
                    bundle,
                    context,
                )
            else:
                refreshed = build_system_messages_for_chat_track(
                    bundle,
                    context,
                    memory_bootstrap_type,
                )
        case CompanionTurnTrack.INNER_TICK_MAINTENANCE:
            refreshed = build_system_messages_for_inner_tick_maintenance(
                bundle,
                context,
                store,
            )
        case CompanionTurnTrack.USER_CHAT:
            refreshed = build_system_messages_for_tool_track(
                bundle,
                context,
            )
        case (
            CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING
            | CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT
            | CompanionTurnTrack.INNER_TICK_SCHEDULED
        ):
            raise RuntimeError(
                "refresh_companion_turn_prompt_stack unsupported track="
                f"{track.value}"
            )
    refreshed = append_runtime_output_format_system_message(
        system_messages=refreshed,
        bundle=bundle,
        runtime_context=runtime_context,
    )
    if runtime_context.channel == CompanionRuntimeChannel.WECHAT_WEIXIN:
        refreshed.append(weixin_clawbot_contact_alias_system_message())
    replace_leading_system_messages_inplace(messages, refreshed)
    return tools_for_turn
