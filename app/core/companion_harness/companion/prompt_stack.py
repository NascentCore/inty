"""Select and refresh the companion prompt stack for each turn track.

The companion turn track is the public routing fact: it decides which tool
schemas are exposed, which system-message wrapper is used, and which route mode
must be enforced.  Mid-turn refreshes re-read MemoryStore and ``context.json`` so
tool-side writes to persona/context documents become visible before the next
model leg continues.

Legacy imperative assembly for greeting, proactive, scheduled, monolog, and dual-LLM
paths. Target memory projection lives in ``prompting.projection`` + ``PromptBuilder`` (#3521).

TODO(!3398): dual-LLM foreground envelope vs single-LLM in-turn sync for settled ``USER_CHAT`` — #3369.

TODO(memory-hierarchy-design): After #3405, define per-track memory load policy from agreed
hierarchy (design issue; options include in-context vs retrieval-required splits).

TODO(memory-projection-pipeline): Converge track assembly onto projection pipeline. — #3521

TODO(world-engine-mailbox-prompt): Inject unread mailbox messages into companion — #3708
prompt slices; user never sees sub-agent directly (epic #3700).
"""

from __future__ import annotations

from typing import Any

from app.core.companion_harness.tools.companion_tool_runtime import (
    build_openai_bootstrap_track_tools,
    build_openai_repl_tools,
    build_openai_repl_tools_inner_tick,
    build_openai_repl_tools_inner_tick_autonomy,
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
from .inner_tick_kind import inner_tick_kind_for_track, inner_tick_spec
from .turn_track import turn_flags_for_track
from .implicit_signal_messages import implicit_user_signed_on_chat_turn
from .runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
    is_im_runtime_channel,
)
from app.core.companion_harness.prompting.tracks import (
    build_settled_user_turn_dual_chat_leg_system_messages,
)
from .prompts.system_messages import (
    build_system_messages_for_implicit_sign_on_greeting,
    build_system_messages_for_inner_tick_proactive_chat,
    build_system_messages_for_inner_tick_scheduled,
    build_system_messages_for_tool_track,
    weixin_clawbot_contact_alias_system_message,
)
from app.core.companion_harness.loop.runtime_system_clauses import (
    append_configured_fixed_reply_language_system_messages,
)
from .turn_routes import TurnRouteMode, resolve_turn_route_mode


def _async_tool_system_messages_for_track(
    *,
    track: CompanionTurnTrack,
    route_mode: TurnRouteMode,
    bundle: PromptBundle,
    context: ContextMeta,
    store: MemoryStore,
) -> list[dict[str, Any]]:
    """Build async tool-path system messages for MONOLOG or AUTONOMY tracks."""
    kind = inner_tick_kind_for_track(track)
    assert kind is not None
    spec = inner_tick_spec(kind)
    builder = spec.async_tool_prompt_builder
    assert builder is not None
    if route_mode != TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL:
        raise RuntimeError(
            f"{spec.turn_track.value} track requires ASYNC route, got "
            f"{route_mode.value}"
        )
    return builder(bundle, context, store)


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
    runtime_channel: ChannelKind,
) -> str:
    """Resolve channel output-format text from the runtime communication medium."""
    match runtime_channel:
        case channel if is_im_runtime_channel(channel):
            return bundle.output_format_im_dm_md
        case ChannelKind.APP_WS | ChannelKind.SMS:
            return ""
        case _:
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
    # TODO(abstraction): The following 3 args should be removed, and reflect the combination in track: CompanionTureTrack — #3453
    inner_tick_turn: bool,
    inner_tick_activity: InnerTickActivity,
    implicit_user_signed_on_turn: bool = False,
    # TODO(companion-channel-tools): Filter tool schemas by ``runtime_context.channel`` — #3362
    # TODO(telegram-meta-ops-tools): Telegram meta tools only when dedicated-bot — #3397 / #3361
) -> list[dict[str, Any]]:
    """OpenAI tool schemas for this turn (independent of which system-message wrapper runs)."""
    match track:
        case CompanionTurnTrack.USER_CHAT_BOOTSTRAP:
            tools_for_turn = build_openai_bootstrap_track_tools()
        case CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING:
            tools_for_turn = []
        case CompanionTurnTrack.INNER_TICK_AUTONOMY:
            tools_for_turn = build_openai_repl_tools_inner_tick_autonomy()
        case _:
            tick_proactive = (
                inner_tick_turn
                and inner_tick_activity == InnerTickActivity.PROACTIVE_CHAT
            )
            # TODO(cross-track-image-delivery): PROACTIVE_CHAT tools=[] — visual offers — #3285
            # need AUTONOMY asset handoff or user-chat tool leg; see #3285 #3468.
            tools_for_turn = (
                []
                if tick_proactive
                else (
                    build_openai_repl_tools_inner_tick()
                    if inner_tick_turn
                    else build_openai_repl_tools()
                )
            )
            if implicit_user_signed_on_turn and not inner_tick_turn:
                tools_for_turn = []
    return tools_for_turn


# TODO(structural-simplicity): Dissolve this function, and let caller directly call the — #3516
# track-denominated system messsages building API.
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
                runtime_context.channel,
            )
        case CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT:
            # TODO(!3463): Compose proactive as overlay on base track prefix — during
            # bootstrap use ``PromptBuilder.bootstrap_turn_system_dicts``, then append
            # proactive-only slices; do not rely on ``interactive_bootstrap_active`` alone
            # (``_persona_system_messages`` also requires ``not inner_tick_turn``).
            # Peripheral cohort via bootstrap track compose (not gateway extras alone) — #3463.
            out = build_system_messages_for_inner_tick_proactive_chat(
                bundle, context, store
            )
        case CompanionTurnTrack.INNER_TICK_SCHEDULED:
            out = build_system_messages_for_inner_tick_scheduled(
                bundle, context
            )
        case (
            CompanionTurnTrack.INNER_TICK_MONOLOG
            | CompanionTurnTrack.INNER_TICK_AUTONOMY
        ):
            out = _async_tool_system_messages_for_track(
                track=track,
                route_mode=route_mode,
                bundle=bundle,
                context=context,
                store=store,
            )
        case CompanionTurnTrack.USER_CHAT_BOOTSTRAP:
            raise RuntimeError(
                "USER_CHAT_BOOTSTRAP system messages must be composed via "
                "PromptBuilder.bootstrap_turn_system_dicts (turn_pipeline)"
            )
        case CompanionTurnTrack.USER_CHAT:
            if (
                route_mode
                != TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL
            ):
                raise RuntimeError(
                    "user_chat track requires ASYNC route, got "
                    f"{route_mode.value}"
                )
            out = build_settled_user_turn_dual_chat_leg_system_messages(
                bundle,
                context,
            )
    # TODO(track-compose-unify): Bootstrap/greeting tracks should use shared bootstrap_turn — #3398
    # compose (peripheral gateway extras + cohort) — #3398.
    out = append_runtime_output_format_system_message(
        system_messages=out,
        bundle=bundle,
        runtime_context=runtime_context,
    )
    if runtime_context.channel == ChannelKind.WECHAT_WEIXIN:
        out.append(weixin_clawbot_contact_alias_system_message())
    # Chat-only tracks (greeting, proactive, scheduled, …) and dual-LLM chat-leg
    # prefixes; bootstrap/settled single-LLM use PromptBuilder instead.
    return append_configured_fixed_reply_language_system_messages(out)


def companion_turn_tools_and_system_messages(
    *,
    store: MemoryStore,
    bundle: PromptBundle,
    context: ContextMeta,
    memory_bootstrap_type: str,
    track: CompanionTurnTrack,
    implicit_user_signed_on_turn: bool = False,
    runtime_context: TurnRuntimeContext = TurnRuntimeContext(
        channel=ChannelKind.APP_WS,
        implicit_signal_bundle=None,
    ),
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], TurnRouteMode]:
    """
    Single source for companion chat-round tools list and system message stack.

    ``USER_CHAT_BOOTSTRAP`` runs one in-turn tool loop so setup can persist
    relationship seed docs via ``memory_store_write_document`` before completion.
    Normal user chat and monolog inner tick require
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
        channel=ChannelKind.APP_WS,
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
            raise RuntimeError(
                "USER_CHAT_BOOTSTRAP mid-turn refresh must use "
                "refresh_single_llm_bootstrap_chat_prompt_prefix"
            )
        case (
            CompanionTurnTrack.INNER_TICK_MONOLOG
            | CompanionTurnTrack.INNER_TICK_AUTONOMY
        ):
            refreshed = _async_tool_system_messages_for_track(
                track=track,
                route_mode=TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL,
                bundle=bundle,
                context=context,
                store=store,
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
    if runtime_context.channel == ChannelKind.WECHAT_WEIXIN:
        refreshed.append(weixin_clawbot_contact_alias_system_message())
    replace_leading_system_messages_inplace(messages, refreshed)
    return tools_for_turn
