"""Scope autonomous inner-tick tracks: monolog, autonomy, dreaming (#3255).

Orchestration only — Postgres reads go through ``inner_tick_scope`` /
``scope_inner_tick_persistence``; kernel due + turns via ``companion_harness.runtime``.
# TODO(dedup-scope-presence-inner-tick): Slice 2 — ``fire_throttled_inner_tick(kind, …, delivery)``
# on ``InnerTickKind`` registry; unify presence/scope fire bodies + throttle stores — #3424.
"""

from __future__ import annotations

import asyncio
import time
import uuid

from loguru import logger

from app.core.companion_harness.companion.dreaming_observability import (
    DreamingBatchOutcome,
)
from app.core.companion_harness.companion.inner_tick_kind import InnerTickKind
from app.core.companion_harness.companion.manager import CompanionSession
from app.core.companion_harness.companion.models import InnerTickThrottleKind
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.runtime.inner_tick_fire import (
    InnerTickKernelInput,
    InnerTickThrottleSnapshot,
    inner_tick_remain_seconds,
    kernel_fire_throttled,
)
from app.core.config import global_config_loaded_from_config_yaml
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.services import companion_chat_service
from app.services.agentic_companion.inner_tick_kernel_context import (
    build_inner_tick_kernel_context,
)
from app.services.agentic_companion.inner_tick_scope import (
    InnerTickChatResolveMode,
    InnerTickModelSource,
    resolve_inner_tick_scope_coords_for_triple,
)
from app.services.agentic_companion.inner_tick_turn_scope import (
    inner_tick_turn_scope,
)
from app.services.agentic_companion.scope_inner_tick_state import (
    get_scope_inner_tick_state,
)
from app.services.agentic_companion.session import InnerTickCoords
from app.utils.models_catalog import GenAIModel


def _scope_throttle_snapshot(
    scope: CompanionScope,
) -> InnerTickThrottleSnapshot:
    tick_state = get_scope_inner_tick_state(scope)
    return InnerTickThrottleSnapshot(
        last_monolog_monotonic=tick_state.last_monolog_inner_tick_monotonic(),
        last_monolog_line_count=tick_state.last_monolog_transcript_line_count(),
        last_autonomy_monotonic=tick_state.last_autonomy_inner_tick_monotonic(),
        last_autonomy_line_count=tick_state.last_autonomy_transcript_line_count(),
    )


async def _scope_kernel_context(
    *,
    resolved_user_id: str,
    resolved_agent_id: str,
    resolved_chat_row_id: str | int,
    resolved_model: GenAIModel,
    scope: CompanionScope,
    preset_uid: str,
    implicit_signal_bundle: ImplicitSignalBundle | None,
) -> tuple[InnerTickKernelInput, CompanionSession] | None:
    return await build_inner_tick_kernel_context(
        user_id=resolved_user_id,
        agent_id=resolved_agent_id,
        chat_row_id=resolved_chat_row_id,
        model_override=resolved_model,
        throttle=_scope_throttle_snapshot(scope),
        runtime_context=TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=implicit_signal_bundle,
        ),
        preset_uid=preset_uid,
        background_output_sink=None,
    )


async def try_fire_autonomy_for_scope(
    *,
    coords: InnerTickCoords,
    poll_source: str,
    chat_resolve_mode: InnerTickChatResolveMode,
    implicit_signal_bundle: ImplicitSignalBundle | None,
) -> bool:
    # TODO(#3473): gate monolog + autonomy + dreaming on token budget before turn_lock.
    """AUTONOMY inner-tick: silent self-directed turn (MemoryStore only, #3255)."""
    resolved = await resolve_inner_tick_scope_coords_for_triple(
        coords=coords,
        poll_source=poll_source,
        model_source=InnerTickModelSource.CHAT_DEFAULT,
        chat_resolve_mode=chat_resolve_mode,
    )
    if resolved is None:
        return False

    scope = CompanionScope(
        user_id=resolved.user_id,
        companion_id=resolved.agent_id,
        chat_id=str(resolved.chat_row_id),
    )
    tick_state = get_scope_inner_tick_state(scope)
    preset_uid = str(uuid.uuid4())
    ctx_pair = await _scope_kernel_context(
        resolved_user_id=resolved.user_id,
        resolved_agent_id=resolved.agent_id,
        resolved_chat_row_id=resolved.chat_row_id,
        resolved_model=resolved.model_override,
        scope=scope,
        preset_uid=preset_uid,
        implicit_signal_bundle=implicit_signal_bundle,
    )
    if ctx_pair is None:
        return False
    kernel_input, scope_session = ctx_pair

    if (
        inner_tick_remain_seconds(
            InnerTickKind.AUTONOMY,
            kernel_input.mem_store,
            kernel_input.throttle,
        )
        > 0
    ):
        return False

    async with inner_tick_turn_scope(session=scope_session):
        tick_state.clear_autonomy_tool_bg_idle_if_idle()
        if tick_state.autonomy_tool_bg_still_running():
            logger.debug(
                "scope_autonomy_inner_tick skipped prev_autonomy_tool_bg poll_source={} user={} agent={}",
                poll_source,
                resolved.user_id,
                resolved.agent_id,
            )
            return False
        try:
            kernel_result = await kernel_fire_throttled(
                InnerTickKind.AUTONOMY,
                kernel_input,
            )
        except Exception as exc:
            logger.warning(
                "scope_autonomy_inner_tick run_turn failed poll_source={} user={} agent={}: {}",
                poll_source,
                resolved.user_id,
                resolved.agent_id,
                exc,
            )
            raise

        companion_turn = kernel_result.turn
        if companion_turn.tool_background_started:
            tick_state.bind_autonomy_tool_bg_idle(
                companion_chat_service.companion_session_tool_bg_idle_event(
                    user_id=resolved.user_id,
                    agent_id=resolved.agent_id,
                    chat_id=resolved.chat_row_id,
                    resolved_chat_model=resolved.model_override,
                )
            )
        else:
            tick_state.bind_autonomy_tool_bg_idle(None)

        if (
            kernel_result.throttle_kind == InnerTickThrottleKind.AUTONOMY
            and kernel_result.throttle_line_count is not None
        ):
            tick_state.mark_autonomy_inner_tick_fired(
                time.monotonic(),
                kernel_result.throttle_line_count,
            )

    logger.info(
        "scope_autonomy_inner_tick fired poll_source={} user={} agent={} chat_id={} tool_background_started={}",
        poll_source,
        resolved.user_id,
        resolved.agent_id,
        resolved.chat_row_id,
        companion_turn.tool_background_started,
    )
    return True


async def try_fire_monolog_for_scope(
    *,
    coords: InnerTickCoords,
    poll_source: str,
    chat_resolve_mode: InnerTickChatResolveMode,
    implicit_signal_bundle: ImplicitSignalBundle | None,
) -> bool:
    """MONOLOG inner-tick without user-visible delivery (MemoryStore only, #3255)."""
    resolved = await resolve_inner_tick_scope_coords_for_triple(
        coords=coords,
        poll_source=poll_source,
        model_source=InnerTickModelSource.CHAT_DEFAULT,
        chat_resolve_mode=chat_resolve_mode,
    )
    if resolved is None:
        return False

    scope = CompanionScope(
        user_id=resolved.user_id,
        companion_id=resolved.agent_id,
        chat_id=str(resolved.chat_row_id),
    )
    tick_state = get_scope_inner_tick_state(scope)
    preset_uid = str(uuid.uuid4())
    ctx_pair = await _scope_kernel_context(
        resolved_user_id=resolved.user_id,
        resolved_agent_id=resolved.agent_id,
        resolved_chat_row_id=resolved.chat_row_id,
        resolved_model=resolved.model_override,
        scope=scope,
        preset_uid=preset_uid,
        implicit_signal_bundle=implicit_signal_bundle,
    )
    if ctx_pair is None:
        return False
    kernel_input, scope_session = ctx_pair

    if (
        inner_tick_remain_seconds(
            InnerTickKind.MONOLOG,
            kernel_input.mem_store,
            kernel_input.throttle,
        )
        > 0
    ):
        return False

    async with inner_tick_turn_scope(session=scope_session):
        tick_state.clear_monolog_tool_bg_idle_if_idle()
        if tick_state.monolog_tool_bg_still_running():
            logger.debug(
                "scope_monolog_inner_tick skipped prev_monolog_tool_bg poll_source={} user={} agent={}",
                poll_source,
                resolved.user_id,
                resolved.agent_id,
            )
            return False
        try:
            kernel_result = await kernel_fire_throttled(
                InnerTickKind.MONOLOG,
                kernel_input,
            )
        except Exception as exc:
            logger.warning(
                "scope_monolog_inner_tick run_turn failed poll_source={} user={} agent={}: {}",
                poll_source,
                resolved.user_id,
                resolved.agent_id,
                exc,
            )
            raise

        if kernel_result is None:
            return False

        companion_turn = kernel_result.turn
        if companion_turn.tool_background_started:
            tick_state.bind_monolog_tool_bg_idle(
                companion_chat_service.companion_session_tool_bg_idle_event(
                    user_id=resolved.user_id,
                    agent_id=resolved.agent_id,
                    chat_id=resolved.chat_row_id,
                    resolved_chat_model=resolved.model_override,
                )
            )
        else:
            tick_state.bind_monolog_tool_bg_idle(None)

        if (
            kernel_result.throttle_kind == InnerTickThrottleKind.MONOLOG
            and kernel_result.throttle_line_count is not None
        ):
            tick_state.mark_monolog_inner_tick_fired(
                time.monotonic(),
                kernel_result.throttle_line_count,
            )

    logger.info(
        "scope_monolog_inner_tick fired poll_source={} user={} agent={} chat_id={} tool_background_started={}",
        poll_source,
        resolved.user_id,
        resolved.agent_id,
        resolved.chat_row_id,
        companion_turn.tool_background_started,
    )
    return True


async def try_fire_dreaming_for_scope(
    *,
    coords: InnerTickCoords,
    poll_source: str,
) -> bool:
    """Dreaming inner-tick for one scope without signed-on presence (#3255).

    Authoritative due check runs inside ``run_dreaming_batch_if_due`` after ``turn_lock``.
    """
    resolved = await resolve_inner_tick_scope_coords_for_triple(
        coords=coords,
        poll_source=poll_source,
        model_source=InnerTickModelSource.DREAMING_HARNESS,
        chat_resolve_mode=InnerTickChatResolveMode.READ_ONLY,
    )
    if resolved is None:
        return False

    idle_seconds = (
        global_config_loaded_from_config_yaml.agent.companion_harness.dreaming_idle_seconds
    )

    scope_session = (
        await companion_chat_service.resolve_companion_session_for_api_turn(
            user_id=resolved.user_id,
            agent_id=resolved.agent_id,
            chat_id=resolved.chat_row_id,
            resolved_chat_model=resolved.model_override,
            session_id=None,
        )
    )
    async with inner_tick_turn_scope(session=scope_session):
        outcome = await asyncio.to_thread(
            companion_chat_service.run_dreaming_batch_for_api,
            user_id=resolved.user_id,
            agent_id=resolved.agent_id,
            chat_id=resolved.chat_row_id,
            resolved_chat_model=resolved.model_override,
            dreaming_idle_seconds=idle_seconds,
        )
        if outcome == DreamingBatchOutcome.CHECKPOINT_SAVED:
            logger.info(
                "companion_dreaming checkpoint_saved poll_source={} user={} agent={} chat={}",
                poll_source,
                resolved.user_id,
                resolved.agent_id,
                resolved.chat_row_id,
            )
            # TODO(dreaming-completion-notify): #3744 — wake in-process waiters / WS meta
            # instead of relying on external Postgres polling in regression driver.
        return outcome == DreamingBatchOutcome.CHECKPOINT_SAVED
