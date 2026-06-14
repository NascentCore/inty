"""Inner-tick turn execution: presence delivery tracks + scope autonomous tracks.

TODO(#3400): Rename maintenance inner-tick to monolog track/activity + wire meta
(``companion_maintenance_inner_tick`` → monolog); behavior narrow stays #3375.

**Presence** (``try_fire_proactive_*``, ``try_fire_scheduled_*``): persists chat history
and delivers assistant output via :class:`InnerTickDelivery`. WS wire envelopes are built
here; Weixin receives plain text through the same path.

**Scope** (``scope_inner_tick_fire``): maintenance, autonomy, dreaming — orchestration only;
Postgres reads in ``inner_tick_scope_resolver`` / ``scope_inner_tick_persistence``;
MemoryStore writes via ``companion_chat_service``. Throttle in ``scope_inner_tick_state``.

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

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from loguru import logger

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
from app.db.session import AsyncSessionLocal
from app.schemas.biz_action import ActionType, BizAction
from app.schemas.chat import ChatCompletionRequest, ChatMessage
from app.schemas.chat_websocket import (
    ChatWsCompanionWireMessageMetaData,
    dump_chat_ws_companion_wire_meta,
)
from app.schemas.response import APIResponse
from app.services import (
    chat_history_service,
    companion_chat_service,
)
from app.services.chat_service import generate_session_id
from app.services.agentic_companion.inner_tick_delivery import (
    InnerTickDelivery,
    deliver_inner_tick_assistant,
)
from app.services.agentic_companion.inner_tick_scope_resolver import (
    InnerTickChatResolveMode,
    InnerTickModelSource,
    InnerTickScopeCoords,
    resolve_inner_tick_scope_coords,
)
from app.services.agentic_companion.inner_tick_turn_scope import inner_tick_turn_scope
from app.services.agentic_companion.scope_inner_tick_fire import (
    try_fire_autonomy_for_scope,
    try_fire_dreaming_for_scope,
    try_fire_maintenance_for_scope,
)
from app.services.agentic_companion.session import Coordinator, InnerTickCoords
from app.services.agentic_companion.ws_implicit_signals import (
    implicit_signal_bundle_from_tc_box,
)


@dataclass(frozen=True)
class InnerTickFireInput:
    """Bundled arguments for one inner-tick ``try_fire_*`` attempt on a presence wire."""

    delivery: InnerTickDelivery
    coords: InnerTickCoords
    coordinator: Coordinator
    ws_conn_id: str
    tc_box: list[Optional[dict]]


async def _resolve_inner_tick_scope_coords(
    fire_input: InnerTickFireInput,
    *,
    model_source: InnerTickModelSource,
    chat_resolve_mode: InnerTickChatResolveMode,
) -> InnerTickScopeCoords | None:
    """Load user/chat and model for one inner-tick attempt."""
    return await resolve_inner_tick_scope_coords(
        coords=fire_input.coords,
        poll_source=fire_input.ws_conn_id,
        model_source=model_source,
        chat_resolve_mode=chat_resolve_mode,
    )


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
    async with inner_tick_turn_scope(session=scope_session):
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
    async with inner_tick_turn_scope(session=scope_session):
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


async def try_fire_dreaming_inner_tick(
    fire_input: InnerTickFireInput,
) -> bool:
    """Presence-path delegator; scope worker should call ``try_fire_dreaming_for_scope``."""
    return await try_fire_dreaming_for_scope(
        coords=fire_input.coords,
        poll_source=fire_input.ws_conn_id,
    )
