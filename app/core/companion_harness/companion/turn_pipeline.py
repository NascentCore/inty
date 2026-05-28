"""Stage contracts for preparing one production companion turn.

The runtime behavior still lives in ``turn._run_companion_turn_core``. This module names the
front half of that function as explicit stages so the production pipeline can
be split without changing WebSocket, MemoryStore, or tool-background behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loguru import logger

from app.core.config import (
    global_config_loaded_from_config_yaml as _global_config,
)
from app.schemas.implicit_signals import ImplicitSignalBundle

from .proactive_chat import (
    PROACTIVE_CHAT_SYNTHETIC_SYSTEM_MESSAGE,
    PROACTIVE_CHAT_TRANSCRIPT_USER_MARKER,
)
from .implicit_signal_messages import (
    USER_SIGNED_ON_TRIGGER_USER_TEXT,
    implicit_user_signed_on_chat_turn,
)
from app.core.companion_harness.memory.memory_pipeline import (
    MemoryPipelineConfig,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)
from app.core.companion_harness.prompting.bundle import PromptBundle
from .models import (
    INNER_TICK_SYNTHETIC_USER_TEXT,
    TRANSCRIPT_WINDOW_MAX_MESSAGES,
    AssistantTurnSource,
    ChatMessage,
    CompanionTurnTrack,
    ContextMeta,
    InnerTickActivity,
    companion_turn_transcript_loaded_messages,
    load_context_meta,
    load_prompt_bundle,
    transcript_for_llm_turn,
)
from .turn_track import turn_flags_for_track
from .dreaming import (
    apply_dreaming_checkpoint_to_prompt_rows,
    load_dreaming_state,
)
from .prompt_stack import companion_turn_tools_and_system_messages
from app.core.companion_harness.memory.transcript_compaction import (
    CompactionConfig as TranscriptCompactionConfig,
    ConversationCompactor,
    load_compaction_state_from_store,
    save_compaction_state_to_store,
    transcript_compaction_meta_from_outcome,
    transcript_rows_to_openai_dialogue,
)
from .turn_routes import TurnRouteMode
from .user_time_context_llm_slice import (
    build_companion_user_time_context_system_content,
)


@dataclass(frozen=True)
class CompanionTurnRuntimeFlags:
    """Input-normalization decisions made before loading companion state."""

    effective_user_text: str
    tick_proactive: bool
    route_inner_activity: InnerTickActivity
    implicit_sign_on_turn: bool
    turn_type: AssistantTurnSource


@dataclass(frozen=True)
class CompanionTurnLoadedState:
    """MemoryStore state needed to assemble one LLM request."""

    context: ContextMeta
    bundle: PromptBundle
    loaded_transcript: list[ChatMessage]
    transcript_window: list[ChatMessage]
    window_cap: int
    rel_main_transcript: str
    rel_inner_tick_transcript: str
    compaction_turn_idx: int


@dataclass(frozen=True)
class CompanionTurnPromptPlan:
    """Prompt, tools, and route selected for one companion turn."""

    tools_for_turn: list[dict[str, Any]]
    system_messages: list[dict[str, Any]]
    route_mode: TurnRouteMode
    messages: list[dict[str, Any]]
    use_dual_structured_chat: bool
    transcript_compaction: dict[str, Any] | None = None


def resolve_turn_runtime_flags(
    *,
    track: CompanionTurnTrack,
    user_text: str,
    implicit_signal_bundle: ImplicitSignalBundle | None,
) -> CompanionTurnRuntimeFlags:
    """Normalize user text and turn labels before MemoryStore reads."""
    inner_tick_turn, route_inner_activity = turn_flags_for_track(track)
    tick_proactive = track == CompanionTurnTrack.INNER_TICK_PROACTIVE_CHAT
    tick_scheduled = track == CompanionTurnTrack.INNER_TICK_SCHEDULED
    implicit_sign_on_turn = (
        track == CompanionTurnTrack.IMPLICIT_SIGN_ON_GREETING
    )
    effective_user_text = user_text
    if tick_scheduled:
        assert (
            user_text.strip()
        ), "inner_tick_scheduled requires non-empty scheduled_user_text"
        effective_user_text = user_text
    elif inner_tick_turn:
        effective_user_text = (
            PROACTIVE_CHAT_TRANSCRIPT_USER_MARKER
            if tick_proactive
            else INNER_TICK_SYNTHETIC_USER_TEXT
        )
    turn_type: AssistantTurnSource
    if inner_tick_turn:
        turn_type = "inner_tick"
    elif implicit_sign_on_turn:
        turn_type = "greeting"
    else:
        turn_type = "chat"
    return CompanionTurnRuntimeFlags(
        effective_user_text=effective_user_text,
        tick_proactive=tick_proactive,
        route_inner_activity=route_inner_activity,
        implicit_sign_on_turn=implicit_sign_on_turn,
        turn_type=turn_type,
    )


def _companion_tail_user_body_for_llm(
    *,
    user_text: str,
    implicit_sign_on_turn: bool,
) -> str:
    """Tail **user** message body only (no wall-clock lines; those go in a separate system slice)."""
    return (
        USER_SIGNED_ON_TRIGGER_USER_TEXT if implicit_sign_on_turn else user_text
    )


def _companion_user_time_context_system_for_llm(
    *,
    implicit_signal_bundle: ImplicitSignalBundle | None,
) -> str | None:
    """Optional ``## user-time-context`` system body from ``client_time``, or ``None``."""
    enabled = bool(
        _global_config.app.features.experimental_enable_chat_with_user_time_context
    )
    ctx = None
    if implicit_signal_bundle and implicit_signal_bundle.client_time:
        ctx = implicit_signal_bundle.client_time.model_dump(exclude_none=True)
    return build_companion_user_time_context_system_content(
        ctx, enabled=enabled
    )


def load_companion_turn_state(
    *,
    store: MemoryStore,
    inner_tick_turn: bool,
    route_inner_activity: InnerTickActivity,
    transcript_llm_window_max_messages: int | None,
) -> CompanionTurnLoadedState:
    """Load context, prompt bundle, and transcript head for one turn."""
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    context = load_context_meta(store=store)
    bundle = load_prompt_bundle(store, meta=context)
    rel_main_tr = paths.transcript
    rel_inner_tr = paths.transcript_inner_tick
    loaded = companion_turn_transcript_loaded_messages(
        store,
        rel_main_transcript=rel_main_tr,
        rel_inner_tick_transcript=rel_inner_tr,
        inner_tick_turn=inner_tick_turn,
        inner_tick_activity=route_inner_activity,
    )
    if not inner_tick_turn:
        loaded = apply_dreaming_checkpoint_to_prompt_rows(
            loaded, load_dreaming_state(store)
        )
    window_cap = (
        transcript_llm_window_max_messages
        if transcript_llm_window_max_messages is not None
        else TRANSCRIPT_WINDOW_MAX_MESSAGES
    )
    transcript = transcript_for_llm_turn(loaded, max_messages=window_cap)
    prior_user_turns = sum(1 for m in loaded if m.role == "user")
    return CompanionTurnLoadedState(
        context=context,
        bundle=bundle,
        loaded_transcript=loaded,
        transcript_window=transcript,
        window_cap=window_cap,
        rel_main_transcript=rel_main_tr,
        rel_inner_tick_transcript=rel_inner_tr,
        compaction_turn_idx=prior_user_turns + 1,
    )


def build_companion_turn_prompt_plan(
    *,
    store: MemoryStore,
    loaded_state: CompanionTurnLoadedState,
    user_text: str,
    memory_bootstrap_type: str,
    track: CompanionTurnTrack,
    tick_proactive: bool,
    implicit_signal_bundle: ImplicitSignalBundle | None,
    implicit_sign_on_turn: bool,
    transcript_compaction: TranscriptCompactionConfig | None,
) -> CompanionTurnPromptPlan:
    """Assemble system messages, route, and final request messages."""
    inner_tick_turn, _route_inner_activity = turn_flags_for_track(track)
    paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS
    tools_for_turn, system_messages, route_mode = (
        companion_turn_tools_and_system_messages(
            store=store,
            bundle=loaded_state.bundle,
            context=loaded_state.context,
            memory_bootstrap_type=memory_bootstrap_type,
            track=track,
            implicit_user_signed_on_turn=implicit_sign_on_turn,
        )
    )
    use_dual_structured_chat = (
        (not inner_tick_turn)
        and (not tools_for_turn)
        and route_mode != TurnRouteMode.ASYNC_FOREGROUND_CHAT_BACKGROUND_TOOL
    )

    transcript_compaction_meta: dict[str, Any] | None = None
    if transcript_compaction is not None and not inner_tick_turn:
        rel_compact = paths.context_compaction_state_json
        prior_state = load_compaction_state_from_store(store, rel_compact)
        compactor = ConversationCompactor(
            transcript_compaction,
            initial_state=prior_state,
        )
        pre_user: list[dict[str, Any]] = [
            *system_messages,
            *transcript_rows_to_openai_dialogue(loaded_state.transcript_window),
        ]
        outcome = compactor.maybe_compact(
            messages=pre_user,
            turn=loaded_state.compaction_turn_idx,
        )
        messages = list(outcome.messages)
        max_cc = transcript_compaction.max_context_chars
        transcript_compaction_meta = transcript_compaction_meta_from_outcome(
            outcome, max_context_chars=max_cc
        )
        logger.debug(
            "run_turn transcript_compaction_eval did_compact={} reason={} before={} "
            "after={} max_context_chars={} compaction_count={}",
            outcome.did_compact,
            outcome.reason,
            outcome.approx_chars_before,
            outcome.approx_chars_after,
            max_cc,
            outcome.state.compaction_count,
        )
        if outcome.did_compact:
            save_compaction_state_to_store(store, rel_compact, outcome.state)
            logger.info(
                "run_turn transcript_compaction did_compact=true reason={} before={} after={} "
                "compaction_count={}",
                outcome.reason,
                outcome.approx_chars_before,
                outcome.approx_chars_after,
                outcome.state.compaction_count,
            )
    else:
        messages = list(system_messages)
        for m in loaded_state.transcript_window:
            messages.append({"role": m.role, "content": m.content})

    if tick_proactive:
        messages.append(
            {
                "role": "system",
                "content": PROACTIVE_CHAT_SYNTHETIC_SYSTEM_MESSAGE,
            }
        )
    time_ctx_system = _companion_user_time_context_system_for_llm(
        implicit_signal_bundle=implicit_signal_bundle,
    )
    if time_ctx_system is not None:
        messages.append({"role": "system", "content": time_ctx_system})
    tail_user = _companion_tail_user_body_for_llm(
        user_text=user_text,
        implicit_sign_on_turn=implicit_sign_on_turn,
    )
    messages.append({"role": "user", "content": tail_user})

    return CompanionTurnPromptPlan(
        tools_for_turn=tools_for_turn,
        system_messages=system_messages,
        route_mode=route_mode,
        messages=messages,
        use_dual_structured_chat=use_dual_structured_chat,
        transcript_compaction=transcript_compaction_meta,
    )
