"""Scope autonomous inner-tick tracks: maintenance, autonomy, dreaming (#3255).

Orchestration only — Postgres reads go through ``inner_tick_scope_resolver`` /
``scope_inner_tick_persistence``; MemoryStore writes go through ``companion_chat_service``.
Process-local throttle lives in ``scope_inner_tick_state``.
"""

from __future__ import annotations

import asyncio
import time
import uuid

from loguru import logger

from app.core.companion_harness.companion.dreaming_observability import (
    DreamingBatchOutcome,
)
from app.core.companion_harness.companion.inner_tick_schedule import (
    InnerTickScheduleOverrides,
    maintenance_transcript_line_count,
    next_inner_tick_wait_seconds,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.config import global_config_loaded_from_config_yaml
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.services import companion_chat_service
from app.services.agentic_companion.inner_tick_scope_resolver import (
    InnerTickChatResolveMode,
    InnerTickModelSource,
    resolve_inner_tick_scope_coords_for_triple,
)
from app.services.agentic_companion.inner_tick_turn_scope import inner_tick_turn_scope
from app.services.agentic_companion.scope_inner_tick_state import (
    get_scope_inner_tick_state,
)
from app.services.agentic_companion.session import InnerTickCoords
from app.services.chat_service import generate_session_id


async def try_fire_autonomy_for_scope(
    *,
    coords: InnerTickCoords,
    poll_source: str,
    chat_resolve_mode: InnerTickChatResolveMode,
    implicit_signal_bundle: ImplicitSignalBundle | None,
) -> bool:
    """AUTONOMY inner-tick: silent self-directed turn (MemoryStore only, #3255)."""
    resolved = await resolve_inner_tick_scope_coords_for_triple(
        coords=coords,
        poll_source=poll_source,
        model_source=InnerTickModelSource.CHAT_DEFAULT,
        chat_resolve_mode=chat_resolve_mode,
    )
    if resolved is None:
        return False

    mem_store = companion_chat_service.companion_memory_store_if_ready(
        user_id=resolved.user_id,
        agent_id=resolved.agent_id,
        chat_id=resolved.chat_row_id,
        resolved_chat_model=resolved.model_override,
    )
    if mem_store is None:
        return False

    scope = CompanionScope(
        user_id=resolved.user_id,
        companion_id=resolved.agent_id,
        chat_id=str(resolved.chat_row_id),
    )
    tick_state = get_scope_inner_tick_state(scope)
    line_count = maintenance_transcript_line_count(mem_store)

    feats = global_config_loaded_from_config_yaml.app.features
    remain = next_inner_tick_wait_seconds(
        mem_store,
        last_inner_fire_monotonic=tick_state.last_autonomy_inner_tick_monotonic(),
        last_maintenance_transcript_line_count=(
            tick_state.last_autonomy_transcript_line_count()
        ),
        overrides=InnerTickScheduleOverrides(
            enabled=True,
            min_gap_seconds=float(
                feats.companion_ws_maintenance_inner_tick_min_gap_seconds
            ),
            poll_seconds=float(feats.companion_ws_proactive_chat_poll_seconds),
        ),
    )
    if remain > 0:
        return False

    session_id = generate_session_id(str(resolved.chat_row_id))
    preset_uid = str(uuid.uuid4())

    scope_session = await companion_chat_service.resolve_companion_session_for_api_turn(
        user_id=resolved.user_id,
        agent_id=resolved.agent_id,
        chat_id=resolved.chat_row_id,
        resolved_chat_model=resolved.model_override,
        session_id=session_id,
    )
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
            companion_turn = (
                await companion_chat_service.run_companion_api_track_turn_with_lock_held(
                    track_path="inner_tick_autonomy",
                    user_id=resolved.user_id,
                    agent_id=resolved.agent_id,
                    chat_id=resolved.chat_row_id,
                    resolved_chat_model=resolved.model_override,
                    user_chars=0,
                    session_id=session_id,
                    run_track=lambda manager, session: manager.run_inner_tick_autonomy_turn(
                        session,
                        background_output_sink=None,
                        preset_user_msg_uuid=preset_uid,
                        runtime_context=TurnRuntimeContext(
                            channel=CompanionRuntimeChannel.APP,
                            implicit_signal_bundle=implicit_signal_bundle,
                        ),
                    ),
                )
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

        tick_state.mark_autonomy_inner_tick_fired(time.monotonic(), line_count)

    logger.info(
        "scope_autonomy_inner_tick fired poll_source={} user={} agent={} chat_id={} tool_background_started={}",
        poll_source,
        resolved.user_id,
        resolved.agent_id,
        resolved.chat_row_id,
        companion_turn.tool_background_started,
    )
    return True


async def try_fire_maintenance_for_scope(
    *,
    coords: InnerTickCoords,
    poll_source: str,
    chat_resolve_mode: InnerTickChatResolveMode,
    implicit_signal_bundle: ImplicitSignalBundle | None,
) -> bool:
    """MAINTENANCE inner-tick without user-visible delivery (MemoryStore only, #3255)."""
    resolved = await resolve_inner_tick_scope_coords_for_triple(
        coords=coords,
        poll_source=poll_source,
        model_source=InnerTickModelSource.CHAT_DEFAULT,
        chat_resolve_mode=chat_resolve_mode,
    )
    if resolved is None:
        return False

    mem_store = companion_chat_service.companion_memory_store_if_ready(
        user_id=resolved.user_id,
        agent_id=resolved.agent_id,
        chat_id=resolved.chat_row_id,
        resolved_chat_model=resolved.model_override,
    )
    if mem_store is None:
        return False

    scope = CompanionScope(
        user_id=resolved.user_id,
        companion_id=resolved.agent_id,
        chat_id=str(resolved.chat_row_id),
    )
    tick_state = get_scope_inner_tick_state(scope)
    line_count = maintenance_transcript_line_count(mem_store)

    feats = global_config_loaded_from_config_yaml.app.features
    remain = next_inner_tick_wait_seconds(
        mem_store,
        last_inner_fire_monotonic=tick_state.last_maintenance_inner_tick_monotonic(),
        last_maintenance_transcript_line_count=(
            tick_state.last_maintenance_transcript_line_count()
        ),
        overrides=InnerTickScheduleOverrides(
            enabled=True,
            min_gap_seconds=float(
                feats.companion_ws_maintenance_inner_tick_min_gap_seconds
            ),
            poll_seconds=float(feats.companion_ws_proactive_chat_poll_seconds),
        ),
    )
    if remain > 0:
        return False

    session_id = generate_session_id(str(resolved.chat_row_id))
    preset_uid = str(uuid.uuid4())

    scope_session = await companion_chat_service.resolve_companion_session_for_api_turn(
        user_id=resolved.user_id,
        agent_id=resolved.agent_id,
        chat_id=resolved.chat_row_id,
        resolved_chat_model=resolved.model_override,
        session_id=session_id,
    )
    async with inner_tick_turn_scope(session=scope_session):
        tick_state.clear_maintenance_tool_bg_idle_if_idle()
        if tick_state.maintenance_tool_bg_still_running():
            logger.debug(
                "scope_maintenance_inner_tick skipped prev_maintenance_tool_bg poll_source={} user={} agent={}",
                poll_source,
                resolved.user_id,
                resolved.agent_id,
            )
            return False
        try:
            companion_turn = await companion_chat_service.run_companion_api_track_turn_with_lock_held(
                track_path="inner_tick_maintenance",
                user_id=resolved.user_id,
                agent_id=resolved.agent_id,
                chat_id=resolved.chat_row_id,
                resolved_chat_model=resolved.model_override,
                user_chars=0,
                session_id=session_id,
                run_track=lambda manager, session: manager.run_inner_tick_maintenance_turn(
                    session,
                    background_output_sink=None,
                    preset_user_msg_uuid=preset_uid,
                    runtime_context=TurnRuntimeContext(
                        channel=CompanionRuntimeChannel.APP,
                        implicit_signal_bundle=implicit_signal_bundle,
                    ),
                ),
            )
        except Exception as exc:
            logger.warning(
                "scope_maintenance_inner_tick run_turn failed poll_source={} user={} agent={}: {}",
                poll_source,
                resolved.user_id,
                resolved.agent_id,
                exc,
            )
            raise

        if companion_turn.tool_background_started:
            tick_state.bind_maintenance_tool_bg_idle(
                companion_chat_service.companion_session_tool_bg_idle_event(
                    user_id=resolved.user_id,
                    agent_id=resolved.agent_id,
                    chat_id=resolved.chat_row_id,
                    resolved_chat_model=resolved.model_override,
                )
            )
        else:
            tick_state.bind_maintenance_tool_bg_idle(None)

        tick_state.mark_maintenance_inner_tick_fired(time.monotonic(), line_count)

    logger.info(
        "scope_maintenance_inner_tick fired poll_source={} user={} agent={} chat_id={} tool_background_started={}",
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

    mem_store = companion_chat_service.companion_memory_store_if_ready(
        user_id=resolved.user_id,
        agent_id=resolved.agent_id,
        chat_id=resolved.chat_row_id,
        resolved_chat_model=resolved.model_override,
    )
    if mem_store is None:
        return False

    idle_seconds = (
        global_config_loaded_from_config_yaml.app.features.companion_harness.dreaming_idle_seconds
    )

    scope_session = await companion_chat_service.resolve_companion_session_for_api_turn(
        user_id=resolved.user_id,
        agent_id=resolved.agent_id,
        chat_id=resolved.chat_row_id,
        resolved_chat_model=resolved.model_override,
        session_id=None,
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
        return outcome == DreamingBatchOutcome.CHECKPOINT_SAVED
