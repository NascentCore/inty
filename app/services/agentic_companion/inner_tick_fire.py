"""Inner-tick turn execution: scheduled, proactive, maintenance, dreaming (WS + Weixin delivery).

Persists chat history and delivers assistant output via :class:`InnerTickDelivery`.
WS wire envelopes are built here; Weixin receives plain text through the same path.

Locking: each ``try_fire_*`` acquires **presence** ``coordinator.turn_lock``. User chat on
the same wire also holds ``turn_lock`` — inner ticks (including dreaming) and user messages
queue on one connection. Prototype: single presence per paired user (``companion_harness``
AGENTS.md); no scope mutex for multiple ``turn_lock`` on the same scope.

TODO(dreaming-cluster-lock): Multi-process backend needs Postgres advisory lock around
dreaming batches — https://github.com/NascentCore/inty/issues/3271

TODO(inner-tick-fire-delivery-dedup): Extract shared WS / chat_history response assembly
for proactive, scheduled, and maintenance delivery tracks after #3255 scope/presence split.

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

from app.api.v1.endpoints.chat import (
    _agent_status_line_for_chat_header,
    _build_chat_response,
    _normalize_chat_response_content,
)
from app.api.v1.endpoints.chat_ws_companion_support import (
    _companion_ai_meta_from_turn_result,
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
from app.services.agentic_companion.session import Coordinator, InnerTickCoords
from app.services.agentic_companion.ws_implicit_signals import (
    implicit_signal_bundle_from_tc_box,
)
from app.utils.models_catalog import GenAIModel, resolve_chat_text_model


class InnerTickModelSource(StrEnum):
    """Which model id to bind when resolving scope for an inner-tick fire attempt."""

    CHAT_DEFAULT = "chat_default"
    DREAMING_HARNESS = "dreaming_harness"


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
) -> InnerTickScopeCoords | None:
    """Load user/chat and model for one inner-tick attempt."""
    coords = fire_input.coords
    user_id = coords.user_id
    agent_id = coords.agent_id
    chat_id_raw = coords.chat_id

    async with AsyncSessionLocal() as pre_db:
        r_user = await pre_db.execute(select(User).where(User.id == user_id))
        current_user = r_user.scalar_one_or_none()
        if current_user is None:
            return None

        chat = await chat_service.get_or_create_chat_by_agent(
            db=pre_db, user_id=user_id, agent_id=agent_id
        )
        if str(chat.id) != str(chat_id_raw):
            logger.debug(
                "inner_tick_scope chat_id mismatch ws_conn_id={} ctx={} db_chat_id={}",
                fire_input.ws_conn_id,
                chat_id_raw,
                chat.id,
            )
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
    coordinator: Coordinator,
) -> AsyncIterator[None]:
    """Acquire presence ``turn_lock`` for one inner-tick activity."""
    async with coordinator.turn_lock:
        yield


# TODO(inner-tick-fire-dedup): Collapse the four ``try_fire_*`` bodies after delivery-track
# split (#3255); shared pre-check lives in ``_resolve_inner_tick_scope_coords`` today.
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
    async with _inner_tick_turn_scope(coordinator=coordinator):
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
            companion_turn = await companion_chat_service.run_companion_inner_tick_scheduled_turn_for_api(
                scheduled_user_text=synthetic_user_text,
                user_id=user_id,
                agent_id=agent_id,
                chat_id=chat_row_id,
                resolved_chat_model=model_override,
                session_id=session_id,
                background_output_sink=None,
                preset_user_msg_uuid=preset_uid,
                implicit_signal_bundle=ws_implicit,
                runtime_channel=delivery.runtime_channel,
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

        companion_ai_meta = _companion_ai_meta_from_turn_result(
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
            data = _build_chat_response(
                response_text_content,
                response_content_parts,
                synthetic_user_text,
                latest_message_info,
                None,
                stub_request,
                source_imate_id=None,
                user_message_id=user_message_id,
                subscription_actions=subscription_actions,
                client_local_id=None,
            )
            payload = APIResponse.success(data=data)
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
    async with _inner_tick_turn_scope(coordinator=coordinator):
        coordinator.clear_inner_tick_proactive_tool_bg_idle_if_idle()
        if coordinator.inner_tick_proactive_tool_bg_still_running():
            logger.debug(
                "companion_ws_proactive_chat skipped prev_inner_tick_tool_bg ws_conn_id={} user={} agent={}",
                ws_conn_id,
                user_id,
                agent_id,
            )
            return False
        companion_turn = await companion_chat_service.run_companion_inner_tick_proactive_chat_turn_for_api(
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat_row_id,
            resolved_chat_model=model_override,
            session_id=session_id,
            background_output_sink=None,
            preset_user_msg_uuid=preset_uid,
            implicit_signal_bundle=ws_implicit,
            runtime_channel=delivery.runtime_channel,
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

        companion_ai_meta = _companion_ai_meta_from_turn_result(companion_turn)

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
            data = _build_chat_response(
                response_text_content,
                response_content_parts,
                hb_user_text,
                latest_message_info,
                None,
                stub_request,
                source_imate_id=None,
                user_message_id=user_message_id,
                subscription_actions=subscription_actions,
                client_local_id=None,
            )
            payload = APIResponse.success(data=data)
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


async def try_fire_autonomy_inner_tick(
    fire_input: InnerTickFireInput,
) -> bool:
    """AUTONOMY inner-tick: silent self-directed turn during user idle.

    Reuses ``next_inner_tick_wait_seconds`` for the transcript / bootstrap
    gate (last-line-is-assistant + non-bootstrap context_mode); throttles by
    autonomy's own ``last_autonomy_inner_tick_monotonic`` + the same min_gap
    constant as maintenance. Never delivers ``assistant_text`` to the user
    and never writes a synthetic user-marker line to ``transcript.jsonl`` —
    kernel writes the round to ``transcript_inner_tick.jsonl`` exactly like
    maintenance, but the worker layer here drops the foreground envelope.
    """
    coords = await _resolve_inner_tick_scope_coords(
        fire_input,
        model_source=InnerTickModelSource.CHAT_DEFAULT,
    )
    if coords is None:
        return False

    user_id = coords.user_id
    agent_id = coords.agent_id
    chat_row_id = coords.chat_row_id
    model_override = coords.model_override
    ws_conn_id = fire_input.ws_conn_id
    coordinator = fire_input.coordinator
    tc_box = fire_input.tc_box

    mem_store = companion_chat_service.companion_memory_store_if_ready(
        user_id=user_id,
        agent_id=agent_id,
        chat_id=chat_row_id,
        resolved_chat_model=model_override,
    )
    if mem_store is None:
        return False

    line_count = maintenance_transcript_line_count(mem_store)

    feats = global_config_loaded_from_config_yaml.app.features
    remain = next_inner_tick_wait_seconds(
        mem_store,
        last_inner_fire_monotonic=(
            coordinator.last_autonomy_inner_tick_monotonic()
        ),
        last_maintenance_transcript_line_count=(
            coordinator.last_autonomy_transcript_line_count()
        ),
        overrides=InnerTickScheduleOverrides(
            enabled=True,
            min_gap_seconds=float(
                feats.companion_ws_maintenance_inner_tick_min_gap_seconds
            ),
            poll_seconds=float(
                feats.companion_ws_proactive_chat_poll_seconds
            ),
        ),
    )
    if remain > 0:
        return False

    session_id = generate_session_id(str(chat_row_id))
    ws_implicit = implicit_signal_bundle_from_tc_box(tc_box)
    preset_uid = str(uuid.uuid4())

    async with _inner_tick_turn_scope(coordinator=coordinator):
        coordinator.clear_inner_tick_autonomy_tool_bg_idle_if_idle()
        if coordinator.inner_tick_autonomy_tool_bg_still_running():
            logger.debug(
                "companion_ws_autonomy_inner_tick skipped prev_autonomy_tool_bg ws_conn_id={} user={} agent={}",
                ws_conn_id,
                user_id,
                agent_id,
            )
            return False
        try:
            companion_turn = await companion_chat_service.run_inner_tick_autonomy(
                user_id=user_id,
                agent_id=agent_id,
                chat_id=chat_row_id,
                resolved_chat_model=model_override,
                defer_memory_update=True,
                session_id=session_id,
                background_output_sink=coordinator.background_sink,
                preset_user_msg_uuid=preset_uid,
                implicit_signal_bundle=ws_implicit,
            )
        except Exception as exc:
            logger.warning(
                "companion_ws_autonomy_inner_tick run_turn failed ws_conn_id={} user={} agent={}: {}",
                ws_conn_id,
                user_id,
                agent_id,
                exc,
            )
            raise

        if companion_turn.tool_background_started:
            coordinator.bind_inner_tick_autonomy_tool_bg_idle(
                companion_chat_service.companion_session_tool_bg_idle_event(
                    user_id=user_id,
                    agent_id=agent_id,
                    chat_id=chat_row_id,
                    resolved_chat_model=model_override,
                )
            )
        else:
            coordinator.bind_inner_tick_autonomy_tool_bg_idle(None)

        coordinator.mark_autonomy_inner_tick_fired(
            time.monotonic(),
            line_count,
        )

    logger.info(
        "companion_ws_autonomy_inner_tick fired ws_conn_id={} user={} agent={} chat_id={} tool_background_started={}",
        ws_conn_id,
        user_id,
        agent_id,
        chat_row_id,
        companion_turn.tool_background_started,
    )
    return True


async def try_fire_maintenance_inner_tick(
    fire_input: InnerTickFireInput,
) -> bool:
    """If companion transcript says maintenance inner-tick is due, run one MAINTENANCE turn and queue WS.

    Self-directed ``LIFE_CURRENTS.md`` work lives on ``try_fire_autonomy_inner_tick`` (``AUTONOMY`` track).
    """
    # TODO(tool-bg-idle-starves-user-chat): Foreground often returns tool_bg_only while session
    # tool_bg_idle stays cleared until the bg thread finishes; proactive then holds turn_lock
    # inside run_turn idle wait and queues USER_MESSAGE with no chat reply.
    # https://github.com/NascentCore/inty/issues/3123
    coords = await _resolve_inner_tick_scope_coords(
        fire_input,
        model_source=InnerTickModelSource.CHAT_DEFAULT,
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

    line_count = maintenance_transcript_line_count(mem_store)

    feats = global_config_loaded_from_config_yaml.app.features
    remain = next_inner_tick_wait_seconds(
        mem_store,
        last_inner_fire_monotonic=(
            coordinator.last_maintenance_inner_tick_monotonic()
        ),
        last_maintenance_transcript_line_count=(
            coordinator.last_maintenance_transcript_line_count()
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

    session_id = generate_session_id(str(chat_row_id))

    ws_implicit = implicit_signal_bundle_from_tc_box(tc_box)
    stub_utc = ws_implicit.client_time if ws_implicit else None
    preset_uid = str(uuid.uuid4())
    stub_request = ChatCompletionRequest(
        messages=[
            ChatMessage(
                role="user",
                content=MAINTENANCE_INNER_TICK_CHAT_HISTORY_USER_MARKER,
            )
        ],
        message_id=preset_uid,
        user_time_context=stub_utc,
    )

    async with _inner_tick_turn_scope(coordinator=coordinator):
        if coordinator.inner_tick_maintenance_foreground_pending():
            logger.debug(
                "companion_ws_maintenance_inner_tick skipped prev_inner_tick_pending "
                "ws_conn_id={} user={} agent={}",
                ws_conn_id,
                user_id,
                agent_id,
            )
            return False
        coordinator.set_foreground_pending(
            preset_uid,
            {
                "session_id": session_id,
                "agent_id": agent_id,
                "request": stub_request,
                "effective_local_id": None,
                "ws_inner_tick_maintenance": True,
            },
        )
        try:
            companion_turn = await companion_chat_service.run_companion_inner_tick_maintenance_turn_for_api(
                user_id=user_id,
                agent_id=agent_id,
                chat_id=chat_row_id,
                resolved_chat_model=model_override,
                session_id=session_id,
                background_output_sink=coordinator.background_sink,
                preset_user_msg_uuid=preset_uid,
                implicit_signal_bundle=ws_implicit,
                runtime_channel=delivery.runtime_channel,
            )
        except Exception as exc:
            if not getattr(exc, "companion_tool_background_started", False):
                coordinator.remove_foreground_pending(preset_uid)
            raise

        companion_reply = companion_turn.assistant_text
        reply_stripped = (
            str(companion_reply).strip() if companion_reply is not None else ""
        )

        if not reply_stripped and not companion_turn.tool_background_started:
            coordinator.remove_foreground_pending(preset_uid)
            logger.warning(
                "companion_ws_maintenance_inner_tick empty reply ws_conn_id={} user={} agent={}",
                ws_conn_id,
                user_id,
                agent_id,
            )
            return False

        if not companion_turn.tool_background_started:
            coordinator.remove_foreground_pending(preset_uid)

        user_meta = dump_chat_ws_companion_wire_meta(
            ChatWsCompanionWireMessageMetaData(
                inner_tick=True,
                companion_maintenance_inner_tick=True,
            )
        )
        user_row_id = await chat_history_service.add_user_message_async(
            session_id,
            MAINTENANCE_INNER_TICK_CHAT_HISTORY_USER_MARKER,
            meta_data=user_meta,
        )

        if (
            companion_turn.tool_background_started
            and coordinator.has_foreground_pending(preset_uid)
        ):
            coordinator.update_foreground_pending(
                preset_uid,
                {"foreground_user_message_id": user_row_id},
            )

        ai_message_id = None
        if reply_stripped:
            companion_ai_meta = _companion_ai_meta_from_turn_result(
                companion_turn
            )

            ai_message_id = (
                await chat_history_service.add_ai_message_sync_async(
                    session_id,
                    companion_reply,
                    agent_id=chat_row_agent_id,
                    meta_data=companion_ai_meta,
                )
            )

        async with AsyncSessionLocal() as post_db:
            if reply_stripped:
                (
                    response_text_content,
                    response_content_parts,
                ) = _normalize_chat_response_content(companion_reply)

                latest_message_info = None
                try:
                    if ai_message_id is not None:
                        latest_message_info = await chat_history_service.get_ai_message_info_by_id(
                            post_db, ai_message_id
                        )
                    if latest_message_info is None:
                        latest_message_info = await chat_history_service.get_latest_ai_message_info(
                            post_db, session_id
                        )
                except Exception as e:
                    logger.warning(
                        "companion_ws_maintenance_inner_tick latest_message_info failed ws_conn_id={}: {}",
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
                        "companion_ws_maintenance_inner_tick get_latest_user_message_id failed ws_conn_id={}: {}",
                        ws_conn_id,
                        e,
                    )

                subscription_actions = [
                    BizAction(action_type=ActionType.NONE, message=""),
                ]
                data = _build_chat_response(
                    response_text_content,
                    response_content_parts,
                    MAINTENANCE_INNER_TICK_CHAT_HISTORY_USER_MARKER,
                    latest_message_info,
                    None,
                    stub_request,
                    source_imate_id=None,
                    user_message_id=user_message_id,
                    subscription_actions=subscription_actions,
                    client_local_id=None,
                )
                payload = APIResponse.success(data=data)
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

        coordinator.mark_maintenance_inner_tick_fired(
            time.monotonic(),
            line_count,
        )

    if reply_stripped:
        logger.info(
            "companion_ws_maintenance_inner_tick pushed assistant ws_conn_id={} user={} agent={} chat_id={}",
            ws_conn_id,
            user_id,
            agent_id,
            chat_row_id,
        )
        return True
    else:
        logger.info(
            "companion_ws_maintenance_inner_tick tool_bg_only ws_conn_id={} user={} agent={} chat_id={}",
            ws_conn_id,
            user_id,
            agent_id,
            chat_row_id,
        )
    return True


async def try_fire_dreaming_inner_tick(
    fire_input: InnerTickFireInput,
) -> bool:
    """When companion scope may be due for sleeping-state dreaming, run one batch under ``turn_lock``.

    Authoritative due check runs inside ``run_dreaming_batch_if_due`` after the lock is held.

    TODO(scope-inner-tick-worker): Move off presence poll — scope worker #3255
    (https://github.com/NascentCore/inty/issues/3255); delete this ``try_fire_*`` once
    presence-less inner-tick lands.
    """
    coords = await _resolve_inner_tick_scope_coords(
        fire_input,
        model_source=InnerTickModelSource.DREAMING_HARNESS,
    )
    if coords is None:
        return False

    mem_store = companion_chat_service.companion_memory_store_if_ready(
        user_id=coords.user_id,
        agent_id=coords.agent_id,
        chat_id=coords.chat_row_id,
        resolved_chat_model=coords.model_override,
    )
    if mem_store is None:
        return False

    idle_seconds = (
        global_config_loaded_from_config_yaml.app.features.companion_harness.dreaming_idle_seconds
    )

    async with _inner_tick_turn_scope(coordinator=fire_input.coordinator):
        outcome = await asyncio.to_thread(
            companion_chat_service.run_dreaming_batch_for_api,
            user_id=coords.user_id,
            agent_id=coords.agent_id,
            chat_id=coords.chat_row_id,
            resolved_chat_model=coords.model_override,
            dreaming_idle_seconds=idle_seconds,
        )
        if outcome == DreamingBatchOutcome.CHECKPOINT_SAVED:
            logger.info(
                "companion_ws_dreaming checkpoint_saved ws_conn_id={} user={} agent={} chat={}",
                fire_input.ws_conn_id,
                coords.user_id,
                coords.agent_id,
                coords.chat_row_id,
            )
        return outcome == DreamingBatchOutcome.CHECKPOINT_SAVED
