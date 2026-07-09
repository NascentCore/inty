"""Select and refresh the companion prompt stack for each turn track.

The companion turn track is the public routing fact: it decides which tool
schemas are exposed, and which system-message wrapper is used.  Mid-turn
refreshes re-read MemoryStore and ``context.json`` so
tool-side writes to persona/context documents become visible before the next
model leg continues.

Core stacks for monolog, autonomy, and dual-LLM legs use ``prompting.recipe``.
Greeting, proactive, scheduled, and bootstrap paths use ``PromptBuilder`` /
``TrackPromptComposer``. Target memory projection: ``prompting.projection`` (#3521).

TODO(#3398): dual-LLM foreground envelope vs single-LLM in-turn sync for settled ``USER_CHAT``.

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
    load_context_meta,
    load_prompt_bundle,
)
from .inner_tick_kind import inner_tick_kind_for_track
from .implicit_signal_messages import implicit_user_signed_on_chat_turn
from .runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
    is_im_runtime_channel,
)
from app.core.companion_harness.prompting.leg_kind import PromptLegKind
from app.core.companion_harness.prompting.recipe import (
    compose_system_prefix_for_self_contained_track,
    compose_system_prefix_for_user_chat_leg,
)
from app.core.companion_harness.prompting.system_messages import (
    weixin_clawbot_contact_alias_system_message,
)
from app.core.companion_harness.loop.runtime_system_clauses import (
    append_configured_fixed_reply_language_system_messages,
)

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
    implicit_user_signed_on_turn: bool = False,
    # TODO(abstraction): implicit_user_signed_on_turn should be reflected in track — #3453
    # TODO(companion-channel-tools): Filter tool schemas by ``runtime_context.channel`` — #3362
    # TODO(telegram-meta-ops-tools): Telegram meta tools only when dedicated-bot — #3397 / #3361
) -> list[dict[str, Any]]:
    """OpenAI tool schemas for this turn."""
    match track:
        case CompanionTurnTrack.USER_CHAT_BOOTSTRAP:
            tools_for_turn = build_openai_bootstrap_track_tools()
        case CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING:
            tools_for_turn = []
        case CompanionTurnTrack.INNER_TICK_AUTONOMY:
            tools_for_turn = build_openai_repl_tools_inner_tick_autonomy()
        case CompanionTurnTrack.INNER_TICK_MONOLOG:
            tools_for_turn = build_openai_repl_tools_inner_tick()
        case (
            CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT
            | CompanionTurnTrack.INNER_TICK_SCHEDULED
        ):
            # TODO(cross-track-image-delivery): PROACTIVE_CHAT tools=[] — visual offers — #3285
            # need AUTONOMY asset handoff or user-chat tool leg; see #3285 #3468.
            tools_for_turn = []
        case CompanionTurnTrack.USER_CHAT:
            tools_for_turn = build_openai_repl_tools()
        case _ as unexpected:
            raise AssertionError(
                f"unexpected CompanionTurnTrack for tools: {unexpected!r}"
            )
    if implicit_user_signed_on_turn and track == CompanionTurnTrack.USER_CHAT:
        tools_for_turn = []
    return tools_for_turn


def append_tool_refresh_peripheral_system_slices(
    *,
    system_messages: list[dict[str, Any]],
    bundle: PromptBundle,
    runtime_context: TurnRuntimeContext,
) -> list[dict[str, Any]]:
    """Mid-turn tool refresh peripheral: output format and Weixin alias (no reply-language)."""
    out = append_runtime_output_format_system_message(
        system_messages=system_messages,
        bundle=bundle,
        runtime_context=runtime_context,
    )
    if runtime_context.channel == ChannelKind.WECHAT_WEIXIN:
        out.append(weixin_clawbot_contact_alias_system_message())
    return out


def append_peripheral_system_slices(
    *,
    system_messages: list[dict[str, Any]],
    bundle: PromptBundle,
    runtime_context: TurnRuntimeContext,
) -> list[dict[str, Any]]:
    """Append peripheral gateway slices: output format, Weixin alias, reply-language."""
    out = append_runtime_output_format_system_message(
        system_messages=system_messages,
        bundle=bundle,
        runtime_context=runtime_context,
    )
    if runtime_context.channel == ChannelKind.WECHAT_WEIXIN:
        out.append(weixin_clawbot_contact_alias_system_message())
    return append_configured_fixed_reply_language_system_messages(out)


# TODO(structural-simplicity): Dissolve this function, and let caller directly call the — #3516
# track-denominated system messsages building API.
def companion_core_system_messages_for_track(
    *,
    store: MemoryStore,
    bundle: PromptBundle,
    context: ContextMeta,
    track: CompanionTurnTrack,
    runtime_context: TurnRuntimeContext,
) -> list[dict[str, Any]]:
    """Pick the scenario wrapper from ``CompanionTurnTrack`` (see ``system_messages`` docstring)."""
    match track:
        case CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING:
            raise RuntimeError(
                "IMPLICIT_SIGN_ON_GREETING system messages must be composed via "
                "TrackPromptComposer.system_dicts_for_track (turn_pipeline)"
            )
        case CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT:
            raise RuntimeError(
                "INNER_TICK_PROACTIVE_CHAT system messages must be composed via "
                "TrackPromptComposer.system_dicts_for_track (turn_pipeline)"
            )
        case CompanionTurnTrack.INNER_TICK_SCHEDULED:
            raise RuntimeError(
                "INNER_TICK_SCHEDULED system messages must be composed via "
                "TrackPromptComposer.system_dicts_for_track (turn_pipeline)"
            )
        case (
            CompanionTurnTrack.INNER_TICK_MONOLOG
            | CompanionTurnTrack.INNER_TICK_AUTONOMY
        ):
            out = compose_system_prefix_for_self_contained_track(
                bundle,
                context,
                store,
                track,
            )
        case CompanionTurnTrack.USER_CHAT_BOOTSTRAP:
            raise RuntimeError(
                "USER_CHAT_BOOTSTRAP system messages must be composed via "
                "PromptBuilder.bootstrap_turn_system_dicts (turn_pipeline)"
            )
        case CompanionTurnTrack.USER_CHAT:
            out = compose_system_prefix_for_user_chat_leg(
                bundle,
                context,
                PromptLegKind.CHAT_LEG,
            )
    return append_peripheral_system_slices(
        system_messages=out,
        bundle=bundle,
        runtime_context=runtime_context,
    )


def refresh_companion_turn_prompt_stack(
    *,
    store: MemoryStore,
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
        inner_tick_turn=inner_tick_kind_for_track(track) is not None,
    )
    tools_for_turn = companion_tools_for_turn(
        track=track,
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
            refreshed = compose_system_prefix_for_self_contained_track(
                bundle,
                context,
                store,
                track,
            )
        case CompanionTurnTrack.USER_CHAT:
            refreshed = compose_system_prefix_for_user_chat_leg(
                bundle,
                context,
                PromptLegKind.TOOL_LEG,
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
    refreshed = append_tool_refresh_peripheral_system_slices(
        system_messages=refreshed,
        bundle=bundle,
        runtime_context=runtime_context,
    )
    replace_leading_system_messages_inplace(messages, refreshed)
    return tools_for_turn
