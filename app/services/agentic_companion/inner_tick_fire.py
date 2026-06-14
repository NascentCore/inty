"""Inner-tick turn execution: presence delivery tracks + scope autonomous tracks.

TODO(#3400): Rename maintenance inner-tick to monolog track/activity + wire meta
(``companion_maintenance_inner_tick`` → monolog); behavior narrow stays #3375.

**Presence** (``try_fire_proactive_*``, ``try_fire_scheduled_*``): persists chat history
and delivers assistant output via :class:`InnerTickDelivery`. WS wire envelopes are built
here; Weixin receives plain text through the same path.

**Scope** (``try_fire_*_for_scope``): maintenance, autonomy, dreaming — MemoryStore only,
no signed-on presence (#3255). Throttle lives in ``scope_inner_tick_state``.

Locking: each ``try_fire_*`` acquires **scope** ``CompanionSession.turn_lock`` (#3272).
User chat on the same scope also holds that lock — inner ticks (including dreaming) and
user messages serialize per ``(user_id, agent_id, chat_id)``. Prototype: single presence
per paired user (``companion_harness`` AGENTS.md).

TODO(dreaming-cluster-lock): Multi-process backend needs Postgres advisory lock around
dreaming batches — https://github.com/NascentCore/inty/issues/3271

TODO(scope-maintenance-delivery): User-visible maintenance delivery when offline scope
turn completes moved to undelivered queue — https://github.com/NascentCore/inty/issues/3256

TODO(inner-tick-fire-delivery-dedup): Extract shared WS / chat_history response assembly
for proactive, scheduled, and maintenance delivery tracks; turn meta lives in
``ws_turn_support`` (#3377).

Prototype: inner-tick fire paths do not call ``subscription_service`` (no
``check_chat_limit`` / ``record_usage``). User chat billing stays in ``chat_ws.py``.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional

from loguru import logger
from sqlalchemy import select

from app.services.chat_completion_wire import (
    build_companion_ws_completion_data,
    _normalize_chat_response_content,
)
from app.services.agent_status_line import (
    agent_status_line_for_chat_header as _agent_status_line_for_chat_header,
)
from app.services.agentic_companion.ws_turn_support import (
    companion_ai_meta_from_turn_result,
)
from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.dreaming_observability import (
    DreamingBatchOutcome,
)
from app.core.companion_harness.companion.inner_tick_schedule import (
    InnerTickScheduleOverrides,
    maintenance_transcript_line_count,
    next_inner_tick_wait_seconds,
)
from app.core.companion_harness.companion.models import (
    MAINTENANCE_INNER_TICK_CHAT_HISTORY_USER_MARKER,
)
from app.core.companion_harness.companion.proactive_chat import (
    PROACTIVE_CHAT_TRANSCRIPT_USER_MARKER,
    ProactiveChatConfig,
    next_proactive_chat_wait_seconds,
)
from app.core.companion_harness.companion.schedule_queue import (
    mark_task_fired,
    mark_task_retry,
    next_due_task_for_execution,
    scheduled_task_synthetic_user_text,
)
from app.core.config import global_config_loaded_from_config_yaml
from app.core.model_selection import select_chat_model
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.schemas.biz_action import ActionType, BizAction
from app.schemas.chat import ChatCompletionRequest, ChatMessage
from app.schemas.chat_websocket import (
    ChatWsCompanionWireMessageMetaData,
    dump_chat_ws_companion_wire_meta,
)
from app.schemas.response import APIResponse
from app.services import (
    chat_history_service,
    chat_service,
    companion_chat_service,
)
from app.services.chat_service import generate_session_id
from app.services.agentic_companion.inner_tick_delivery import (
    InnerTickDelivery,
    deliver_inner_tick_assistant,
)
from app.core.companion_harness.companion.scope import CompanionScope
from app.core.companion_harness.companion.manager import CompanionSession
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.services.agentic_companion.scope_inner_tick_state import (
    get_scope_inner_tick_state,
)
from app.services.agentic_companion.session import Coordinator, InnerTickCoords
from app.services.agentic_companion.ws_implicit_signals import (
    implicit_signal_bundle_from_tc_box,
)
from app.core.companion_harness.agent_channel.scope import (
    AgentScope,
    is_agent_scope_memory_store_chat_id,
)
from app.utils.models_catalog import GenAIModel, resolve_chat_text_model


class InnerTickModelSource(StrEnum):
    """Which model id to bind when resolving scope for an inner-tick fire attempt."""

    CHAT_DEFAULT = "chat_default"
    DREAMING_HARNESS = "dreaming_harness"


class InnerTickChatResolveMode(StrEnum):
    """Whether scope resolution may create a missing ``chats`` row."""

    GET_OR_CREATE = "get_or_create"
    READ_ONLY = "read_only"


@dataclass(frozen=True)
class InnerTickFireInput:
    """Bundled arguments for one inner-tick ``try_fire_*`` attempt on a presence wire."""

    delivery: InnerTickDelivery
    coords: InnerTickCoords
    coordinator: Coordinator
    ws_conn_id: str
    tc_box: list[Optional[dict]]


@dataclass(frozen=True)
class InnerTickScopeCoords:
    """Resolved DB scope for inner-tick fire paths (user, agent, chat, model)."""

    user_id: str
    agent_id: str
    chat_row_id: str | int
    chat_row_agent_id: str
    model_override: GenAIModel


async def _resolve_inner_tick_scope_coords(
    fire_input: InnerTickFireInput,
    *,
    model_source: InnerTickModelSource,
    chat_resolve_mode: InnerTickChatResolveMode,
) -> InnerTickScopeCoords | None:
    """Load user/chat and model for one inner-tick attempt."""
    return await _resolve_inner_tick_scope_coords_for_triple(
        coords=fire_input.coords,
        poll_source=fire_input.ws_conn_id,
        model_source=model_source,
        chat_resolve_mode=chat_resolve_mode,
    )


async def _resolve_inner_tick_scope_coords_for_triple(
    *,
    coords: InnerTickCoords,
    poll_source: str,
    model_source: InnerTickModelSource,
    chat_resolve_mode: InnerTickChatResolveMode,
) -> InnerTickScopeCoords | None:
    """Load user/chat and model for one scope triple (presence or scope worker)."""
    user_id = coords.user_id
    agent_id = coords.agent_id
    chat_id_str = str(coords.chat_id)

    async with AsyncSessionLocal() as pre_db:
        r_user = await pre_db.execute(select(User).where(User.id == user_id))
        current_user = r_user.scalar_one_or_none()
        if current_user is None:
            return None

        match model_source:
            case InnerTickModelSource.DREAMING_HARNESS:
                dreaming_llm = (
                    global_config_loaded_from_config_yaml.app.features.companion_harness.dreaming_llm
                )
                model_override = resolve_chat_text_model(dreaming_llm)
            case InnerTickModelSource.CHAT_DEFAULT:
                model_override = select_chat_model(
                    user=current_user,
                    is_subscribed=False,
                )

        if is_agent_scope_memory_store_chat_id(chat_id_str):
            expected = AgentScope(
                user_id=user_id,
                agent_id=agent_id,
            ).memory_store_chat_id()
            if chat_id_str != expected:
                logger.debug(
                    "inner_tick_scope agent-scope chat_id mismatch poll_source={} "
                    "ctx={} expected={}",
                    poll_source,
                    chat_id_str,
                    expected,
                )
                return None
            return InnerTickScopeCoords(
                user_id=user_id,
                agent_id=agent_id,
                chat_row_id=chat_id_str,
                chat_row_agent_id=agent_id,
                model_override=model_override,
            )

        match chat_resolve_mode:
            case InnerTickChatResolveMode.GET_OR_CREATE:
                chat = await chat_service.get_or_create_chat_by_agent(
                    db=pre_db, user_id=user_id, agent_id=agent_id
                )
            case InnerTickChatResolveMode.READ_ONLY:
                chat = await chat_service.get_chat_by_user_and_agent(
                    pre_db, user_id, agent_id
                )
                if chat is None:
                    return None

        if str(chat.id) != chat_id_str:
            logger.debug(
                "inner_tick_scope chat_id mismatch poll_source={} ctx={} db_chat_id={}",
                poll_source,
                chat_id_str,
                chat.id,
            )
            return None

        return InnerTickScopeCoords(
            user_id=user_id,
            agent_id=agent_id,
            chat_row_id=chat.id,
            chat_row_agent_id=chat.agent_id,
            model_override=model_override,
        )


@asynccontextmanager
async def _inner_tick_turn_scope(
    *,
    session: CompanionSession,
) -> AsyncIterator[None]:
    """Acquire scope ``turn_lock`` for one inner-tick activity."""
    async with session.turn_lock:
        yield


# TODO(inner-tick-fire-dedup): Collapse delivery ``try_fire_*`` bodies after scope/presence
# split (#3255) and shared assembly (#3377); pre-check in ``_resolve_inner_tick_scope_coords``.
async def try_fire_scheduled_inner_tick(
    fire_input: InnerTickFireInput,
) -> bool:
    """When ``schedule_queue`` has a due pending task, run one inner-tick reminder turn."""
    # TODO(scheduled-reminder-early-proactive): Proactive chat can read recent
    # reminder context and tell the user "到点了" before a pending schedule_queue
    # task is due. Keep scheduled reminders on this deterministic path only,
    # e.g. gate proactive chat while any future pending reminder exists.
    coords = await _resolve_inner_tick_scope_coords(
        fire_input,
        model_source=InnerTickModelSource.CHAT_DEFAULT,
        chat_resolve_mode=InnerTickChatResolveMode.GET_OR_CREATE,
    )
    if coords is None:
        return False

    user_id = coords.user_id
    agent_id = coords.agent_id
    chat_row_id = coords.chat_row_id
    chat_row_agent_id = coords.chat_row_agent_id
    model_override = coords.model_override
    ws_conn_id = fire_input.ws_conn_id
    coordinator = fire_input.coordinator
    delivery = fire_input.delivery
    tc_box = fire_input.tc_box

    mem_store = companion_chat_service.companion_memory_store_if_ready(
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_row_id,
        resolved_chat_model=model_override,
    )
    if mem_store is None:
        return False

    due_task = next_due_task_for_execution(mem_store)
    if due_task is None:
        return False

    due_task_id = due_task.id
    synthetic_user_text = scheduled_task_synthetic_user_text(
        task_text=due_task.task_text,
        exec_time_utc=due_task.exec_time_utc,
    )

    session_id = generate_session_id(str(chat_row_id))
    preset_uid = str(uuid.uuid4())

    ws_implicit = implicit_signal_bundle_from_tc_box(tc_box)
    scope_session = await companion_chat_service.resolve_companion_session_for_api_turn(
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_row_id,
        resolved_chat_model=model_override,
        session_id=session_id,
    )
    async with _inner_tick_turn_scope(session=scope_session):
        if coordinator.inner_tick_maintenance_foreground_pending():
            logger.debug(
                "companion_ws_scheduled_reminder skipped prev_maintenance_pending "
                "ws_conn_id={} user={} agent={}",
                ws_conn_id,
                user_id,
                agent_id,
            )
            return False
        coordinator.clear_inner_tick_proactive_tool_bg_idle_if_idle()
        if coordinator.inner_tick_proactive_tool_bg_still_running():
            logger.debug(
                "companion_ws_scheduled_reminder skipped prev_inner_tick_tool_bg ws_conn_id={} user={} agent={}",
                ws_conn_id,
                user_id,
                agent_id,
            )
            return False
        try:
            companion_turn = await companion_chat_service.run_companion_api_track_turn_with_lock_held(
                track_path="inner_tick_scheduled",
                user_id=user_id,
                agent_id=agent_id,
                chat_id=chat_row_id,
                resolved_chat_model=model_override,
                user_chars=len(synthetic_user_text),
                session_id=session_id,
                run_track=lambda manager, session: manager.run_inner_tick_scheduled_turn(
                    session,
                    synthetic_user_text,
                    background_output_sink=None,
                    preset_user_msg_uuid=preset_uid,
                    runtime_context=TurnRuntimeContext(
                        channel=delivery.runtime_channel,
                        implicit_signal_bundle=ws_implicit,
                    ),
                ),
            )
        except Exception as exc:
            if not getattr(exc, "companion_tool_background_started", False):
                mark_task_retry(mem_store, due_task_id, str(exc))
                logger.warning(
                    "companion_ws_scheduled_reminder run_turn failed ws_conn_id={} task_id={}: {}",
                    ws_conn_id,
                    due_task_id,
                    exc,
                )
            raise

        if companion_turn.tool_background_started:
            coordinator.bind_inner_tick_proactive_tool_bg_idle(
                companion_chat_service.companion_session_tool_bg_idle_event(
                    user_id=user_id,
                    agent_id=agent_id,
                    chat_id=chat_row_id,
                    resolved_chat_model=model_override,
                )
            )
        else:
            coordinator.bind_inner_tick_proactive_tool_bg_idle(None)

        companion_reply = companion_turn.assistant_text
        reply_stripped = (
            str(companion_reply).strip() if companion_reply is not None else ""
        )
        if not reply_stripped:
            mark_task_retry(mem_store, due_task_id, "empty assistant reply")
            logger.warning(
                "companion_ws_scheduled_reminder empty reply ws_conn_id={} user={} agent={} task_id={}",
                ws_conn_id,
                user_id,
                agent_id,
                due_task_id,
            )
            return True

        user_meta = dump_chat_ws_companion_wire_meta(
            ChatWsCompanionWireMessageMetaData(
                inner_tick=True,
                companion_scheduled_reminder=True,
                scheduled_task_id=due_task_id,
            )
        )
        await chat_history_service.add_user_message_async(
            session_id,
            synthetic_user_text,
            meta_data=user_meta,
        )

        companion_ai_meta = companion_ai_meta_from_turn_result(
            companion_turn,
            companion_scheduled_reminder=True,
            scheduled_task_id=due_task_id,
        )

        ai_message_id = await chat_history_service.add_ai_message_sync_async(
            session_id,
            companion_reply,
            agent_id=chat_row_agent_id,
            meta_data=companion_ai_meta,
        )
        mark_task_fired(mem_store, due_task_id)

        async with AsyncSessionLocal() as post_db:
            stub_utc = ws_implicit.client_time if ws_implicit else None
            stub_request = ChatCompletionRequest(
                messages=[
                    ChatMessage(
                        role="user",
                        content=synthetic_user_text,
                    )
                ],
                message_id=preset_uid,
                user_time_context=stub_utc,
            )
            (
                response_text_content,
                response_content_parts,
            ) = _normalize_chat_response_content(companion_reply)

            latest_message_info = None
            try:
                if ai_message_id is not None:
                    latest_message_info = (
                        await chat_history_service.get_ai_message_info_by_id(
                            post_db, ai_message_id
                        )
                    )
                if latest_message_info is None:
                    latest_message_info = (
                        await chat_history_service.get_latest_ai_message_info(
                            post_db, session_id
                        )
                    )
            except Exception as e:
                logger.warning(
                    "companion_ws_scheduled_reminder latest_message_info failed ws_conn_id={}: {}",
                    ws_conn_id,
                    e,
                )

            user_message_id = None
            try:
                user_message_id = (
                    await chat_history_service.get_latest_user_message_id(
                        post_db, session_id
                    )
                )
            except Exception as e:
                logger.warning(
                    "companion_ws_scheduled_reminder get_latest_user_message_id failed ws_conn_id={}: {}",
                    ws_conn_id,
                    e,
                )

            subscription_actions = [
                BizAction(action_type=ActionType.NONE, message=""),
            ]
            completion = build_companion_ws_completion_data(
                response_text_content=response_text_content,
                response_content_parts=response_content_parts,
                last_user_text=synthetic_user_text,
                latest_message_info=latest_message_info,
                audio_url=None,
                request=stub_request,
                source_imate_id=None,
                user_message_id=user_message_id,
                subscription_actions=subscription_actions,
                client_local_id=None,
            )
            payload = APIResponse.success(
                data=completion.model_dump(exclude_none=True)
            )
            out = payload.model_dump(exclude_none=True)
            out["agent_id"] = agent_id
            out["status_line"] = await _agent_status_line_for_chat_header(
                post_db, agent_id
            )
            await deliver_inner_tick_assistant(
                delivery,
                ws_payload=out,
                assistant_text=response_text_content,
            )
    logger.info(
        "companion_ws_scheduled_reminder pushed assistant ws_conn_id={} user={} agent={} chat_id={} task_id={}",
        ws_conn_id,
        user_id,
        agent_id,
        chat_row_id,
        due_task_id,
    )
    return True


async def try_fire_proactive_chat_inner_tick(
    fire_input: InnerTickFireInput,
) -> bool:
    """If companion transcript says proactive chat is due, run one turn and queue WS payload."""
    coords = await _resolve_inner_tick_scope_coords(
        fire_input,
        model_source=InnerTickModelSource.CHAT_DEFAULT,
        chat_resolve_mode=InnerTickChatResolveMode.GET_OR_CREATE,
    )
    if coords is None:
        return False

    user_id = coords.user_id
    agent_id = coords.agent_id
    chat_row_id = coords.chat_row_id
    chat_row_agent_id = coords.chat_row_agent_id
    model_override = coords.model_override
    ws_conn_id = fire_input.ws_conn_id
    coordinator = fire_input.coordinator
    delivery = fire_input.delivery
    tc_box = fire_input.tc_box

    async with AsyncSessionLocal() as pre_db:
        mem_store = companion_chat_service.companion_memory_store_if_ready(
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat_row_id,
            resolved_chat_model=model_override,
        )
        if mem_store is None:
            return False

        feats = global_config_loaded_from_config_yaml.app.features
        remain = next_proactive_chat_wait_seconds(
            mem_store,
            ProactiveChatConfig(
                base_idle_sec=float(
                    feats.companion_ws_proactive_chat_base_idle_seconds
                ),
                stop_after_silence_minutes=float(
                    feats.companion_ws_proactive_chat_stop_after_silence_minutes
                ),
            ),
        )
        if remain > 0:
            return False

        session_id = generate_session_id(str(chat_row_id))
        preset_uid = str(uuid.uuid4())

    ws_implicit = implicit_signal_bundle_from_tc_box(tc_box)
    scope_session = await companion_chat_service.resolve_companion_session_for_api_turn(
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_row_id,
        resolved_chat_model=model_override,
        session_id=session_id,
    )
    async with _inner_tick_turn_scope(session=scope_session):
        coordinator.clear_inner_tick_proactive_tool_bg_idle_if_idle()
        if coordinator.inner_tick_proactive_tool_bg_still_running():
            logger.debug(
                "companion_ws_proactive_chat skipped prev_inner_tick_tool_bg ws_conn_id={} user={} agent={}",
                ws_conn_id,
                user_id,
                agent_id,
            )
            return False
        companion_turn = await companion_chat_service.run_companion_api_track_turn_with_lock_held(
            track_path="inner_tick_proactive_chat",
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat_row_id,
            resolved_chat_model=model_override,
            user_chars=0,
            session_id=session_id,
            run_track=lambda manager, session: manager.run_inner_tick_proactive_chat_turn(
                session,
                background_output_sink=None,
                preset_user_msg_uuid=preset_uid,
                runtime_context=TurnRuntimeContext(
                    channel=delivery.runtime_channel,
                    implicit_signal_bundle=ws_implicit,
                ),
            ),
        )
        hb_user_text = (
            companion_turn.transcript_user_content
            or PROACTIVE_CHAT_TRANSCRIPT_USER_MARKER
        )
        if companion_turn.tool_background_started:
            coordinator.bind_inner_tick_proactive_tool_bg_idle(
                companion_chat_service.companion_session_tool_bg_idle_event(
                    user_id=user_id,
                    agent_id=agent_id,
                    chat_id=chat_row_id,
                    resolved_chat_model=model_override,
                )
            )
        else:
            coordinator.bind_inner_tick_proactive_tool_bg_idle(None)

        user_meta = dump_chat_ws_companion_wire_meta(
            ChatWsCompanionWireMessageMetaData(
                companion_proactive_chat=True,
                inner_tick=True,
                proactive_chat=True,
            )
        )
        await chat_history_service.add_user_message_async(
            session_id,
            hb_user_text,
            meta_data=user_meta,
        )

        companion_ai_meta = companion_ai_meta_from_turn_result(
            companion_turn,
            companion_scheduled_reminder=None,
            scheduled_task_id=None,
        )

        ai_message_id = await chat_history_service.add_ai_message_sync_async(
            session_id,
            companion_turn.assistant_text,
            agent_id=chat_row_agent_id,
            meta_data=companion_ai_meta,
        )

        async with AsyncSessionLocal() as post_db:
            stub_utc = ws_implicit.client_time if ws_implicit else None
            stub_request = ChatCompletionRequest(
                messages=[
                    ChatMessage(
                        role="user",
                        content=hb_user_text,
                    )
                ],
                message_id=preset_uid,
                user_time_context=stub_utc,
            )
            (
                response_text_content,
                response_content_parts,
            ) = _normalize_chat_response_content(companion_turn.assistant_text)

            latest_message_info = None
            try:
                if ai_message_id is not None:
                    latest_message_info = (
                        await chat_history_service.get_ai_message_info_by_id(
                            post_db, ai_message_id
                        )
                    )
                if latest_message_info is None:
                    latest_message_info = (
                        await chat_history_service.get_latest_ai_message_info(
                            post_db, session_id
                        )
                    )
            except Exception as e:
                logger.warning(
                    "companion_ws_proactive_chat latest_message_info failed ws_conn_id={}: {}",
                    ws_conn_id,
                    e,
                )

            user_message_id = None
            try:
                user_message_id = (
                    await chat_history_service.get_latest_user_message_id(
                        post_db, session_id
                    )
                )
            except Exception as e:
                logger.warning(
                    "companion_ws_proactive_chat get_latest_user_message_id failed ws_conn_id={}: {}",
                    ws_conn_id,
                    e,
                )

            subscription_actions = [
                BizAction(action_type=ActionType.NONE, message=""),
            ]
            completion = build_companion_ws_completion_data(
                response_text_content=response_text_content,
                response_content_parts=response_content_parts,
                last_user_text=hb_user_text,
                latest_message_info=latest_message_info,
                audio_url=None,
                request=stub_request,
                source_imate_id=None,
                user_message_id=user_message_id,
                subscription_actions=subscription_actions,
                client_local_id=None,
            )
            payload = APIResponse.success(
                data=completion.model_dump(exclude_none=True)
            )
            out = payload.model_dump(exclude_none=True)
            out["agent_id"] = agent_id
            out["status_line"] = await _agent_status_line_for_chat_header(
                post_db, agent_id
            )
            await deliver_inner_tick_assistant(
                delivery,
                ws_payload=out,
                assistant_text=response_text_content,
            )
    logger.info(
        "companion_ws_proactive_chat pushed assistant ws_conn_id={} user={} agent={} chat_id={}",
        ws_conn_id,
        user_id,
        agent_id,
        chat_row_id,
    )
    return True


async def try_fire_autonomy_for_scope(
    *,
    coords: InnerTickCoords,
    poll_source: str,
    chat_resolve_mode: InnerTickChatResolveMode,
    implicit_signal_bundle: ImplicitSignalBundle | None,
) -> bool:
    """AUTONOMY inner-tick: silent self-directed turn (MemoryStore only, #3255)."""
    resolved = await _resolve_inner_tick_scope_coords_for_triple(
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
    async with _inner_tick_turn_scope(session=scope_session):
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


async def try_fire_autonomy_inner_tick(
    fire_input: InnerTickFireInput,
) -> bool:
    """Delegator for tests; production scope worker calls ``try_fire_autonomy_for_scope``."""
    return await try_fire_autonomy_for_scope(
        coords=fire_input.coords,
        poll_source=fire_input.ws_conn_id,
        chat_resolve_mode=InnerTickChatResolveMode.GET_OR_CREATE,
        implicit_signal_bundle=implicit_signal_bundle_from_tc_box(fire_input.tc_box),
    )


async def try_fire_maintenance_for_scope(
    *,
    coords: InnerTickCoords,
    poll_source: str,
    chat_resolve_mode: InnerTickChatResolveMode,
    implicit_signal_bundle: ImplicitSignalBundle | None,
) -> bool:
    """MAINTENANCE inner-tick without user-visible delivery (MemoryStore only, #3255)."""
    resolved = await _resolve_inner_tick_scope_coords_for_triple(
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
    async with _inner_tick_turn_scope(session=scope_session):
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


async def try_fire_maintenance_inner_tick(
    fire_input: InnerTickFireInput,
) -> bool:
    """Delegator for tests; production scope worker calls ``try_fire_maintenance_for_scope``."""
    return await try_fire_maintenance_for_scope(
        coords=fire_input.coords,
        poll_source=fire_input.ws_conn_id,
        chat_resolve_mode=InnerTickChatResolveMode.GET_OR_CREATE,
        implicit_signal_bundle=implicit_signal_bundle_from_tc_box(fire_input.tc_box),
    )


async def try_fire_dreaming_for_scope(
    *,
    coords: InnerTickCoords,
    poll_source: str,
) -> bool:
    """Dreaming inner-tick for one scope without signed-on presence (#3255).

    Authoritative due check runs inside ``run_dreaming_batch_if_due`` after ``turn_lock``.
    """
    resolved = await _resolve_inner_tick_scope_coords_for_triple(
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
    async with _inner_tick_turn_scope(session=scope_session):
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


async def try_fire_dreaming_inner_tick(
    fire_input: InnerTickFireInput,
) -> bool:
    """Presence-path delegator; scope worker should call ``try_fire_dreaming_for_scope``."""
    return await try_fire_dreaming_for_scope(
        coords=fire_input.coords,
        poll_source=fire_input.ws_conn_id,
    )
