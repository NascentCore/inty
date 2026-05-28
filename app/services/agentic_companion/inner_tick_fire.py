"""Inner-tick turn execution: scheduled, proactive, maintenance (WS + Weixin delivery).

Persists chat history and delivers assistant output via :class:`InnerTickDelivery`.
WS wire envelopes are built here; Weixin receives plain text through the same path.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Optional

from loguru import logger
from sqlalchemy import select

from app.api.v1.endpoints.chat import (
    _agent_status_line_for_chat_header,
    _build_chat_response,
    _companion_ai_meta_from_turn_result,
    _normalize_chat_response_content,
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
from app.services.agentic_companion.session import Coordinator
from app.services.agentic_companion.ws_implicit_signals import (
    implicit_signal_bundle_from_tc_box,
)
from app.services.subscription_service import SubscriptionService


async def try_fire_scheduled_inner_tick(
    *,
    delivery: InnerTickDelivery,
    ctx: dict[str, Any],
    subscription_svc: SubscriptionService,
    coordinator: Coordinator,
    ws_conn_id: str,
    # TODO(typing): Define a TimeContext Pydantic model and replace this.
    tc_box: list[Optional[dict]],
) -> None:
    """When ``schedule_queue`` has a due pending task, run one inner-tick reminder turn."""
    # TODO(scheduled-reminder-early-proactive): Proactive chat can read recent
    # reminder context and tell the user "到点了" before a pending schedule_queue
    # task is due. Keep scheduled reminders on this deterministic path only,
    # e.g. gate proactive chat while any future pending reminder exists.
    user_id = str(ctx.get("user_id") or "").strip()
    agent_id = str(ctx.get("agent_id") or "").strip()
    chat_id_raw = ctx.get("chat_id")
    if not user_id or not agent_id or chat_id_raw is None:
        return

    async with AsyncSessionLocal() as pre_db:
        r_user = await pre_db.execute(select(User).where(User.id == user_id))
        current_user = r_user.scalar_one_or_none()
        if current_user is None:
            return

        chat = await chat_service.get_or_create_chat_by_agent(
            db=pre_db, user_id=user_id, agent_id=agent_id
        )
        if str(chat.id) != str(chat_id_raw):
            logger.debug(
                "companion_ws_scheduled_reminder chat_id mismatch ws_conn_id={} ctx={} db_chat_id={}",
                ws_conn_id,
                chat_id_raw,
                chat.id,
            )
            return

        subscription = await subscription_svc.get_user_current_subscription(
            pre_db, user_id
        )
        is_subscribed = bool(subscription)
        model_override = select_chat_model(
            user=current_user, is_subscribed=is_subscribed
        )

        mem_store = companion_chat_service.companion_memory_store_if_ready(
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat.id,
            resolved_chat_model=model_override,
        )
        if mem_store is None:
            return

        due_task = next_due_task_for_execution(mem_store)
        if due_task is None:
            return

        is_allowed, used_count, daily_limit = (
            await subscription_svc.check_chat_limit(pre_db, current_user)
        )
        if not is_allowed:
            logger.info(
                "companion_ws_scheduled_reminder skipped subscription ws_conn_id={} user={} used={} limit={}",
                ws_conn_id,
                user_id,
                used_count,
                daily_limit,
            )
            return

        chat_row_id = chat.id
        chat_row_agent_id = chat.agent_id
        due_task_id = due_task.id
        synthetic_user_text = scheduled_task_synthetic_user_text(
            task_text=due_task.task_text,
            exec_time_utc=due_task.exec_time_utc,
        )

    session_id = generate_session_id(str(chat_row_id))
    preset_uid = str(uuid.uuid4())

    ws_implicit = implicit_signal_bundle_from_tc_box(tc_box)
    async with coordinator.turn_lock:
        if coordinator.inner_tick_maintenance_foreground_pending():
            logger.debug(
                "companion_ws_scheduled_reminder skipped prev_maintenance_pending "
                "ws_conn_id={} user={} agent={}",
                ws_conn_id,
                user_id,
                agent_id,
            )
            return
        coordinator.clear_inner_tick_proactive_tool_bg_idle_if_idle()
        if coordinator.inner_tick_proactive_tool_bg_still_running():
            logger.debug(
                "companion_ws_scheduled_reminder skipped prev_inner_tick_tool_bg ws_conn_id={} user={} agent={}",
                ws_conn_id,
                user_id,
                agent_id,
            )
            return
        try:
            companion_turn = await companion_chat_service.run_companion_inner_tick_scheduled_turn_for_api(
                scheduled_user_text=synthetic_user_text,
                user_id=user_id,
                agent_id=agent_id,
                chat_id=chat_row_id,
                resolved_chat_model=model_override,
                defer_memory_update=True,
                session_id=session_id,
                background_output_sink=None,
                preset_user_msg_uuid=preset_uid,
                implicit_signal_bundle=ws_implicit,
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
            return

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
            try:
                await subscription_svc.record_usage(
                    post_db,
                    user_id,
                    "chat",
                    1,
                    extra_data={
                        "agent_id": agent_id,
                        "message_length": 0,
                        "companion_ws_scheduled_reminder": True,
                    },
                )
            except Exception as e:
                logger.warning(
                    "companion_ws_scheduled_reminder record_usage failed ws_conn_id={}: {}",
                    ws_conn_id,
                    str(e),
                )

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


async def try_fire_proactive_chat_inner_tick(
    *,
    delivery: InnerTickDelivery,
    ctx: dict[str, Any],
    subscription_svc: SubscriptionService,
    coordinator: Coordinator,
    ws_conn_id: str,
    tc_box: list[Optional[dict]],
) -> None:
    """If companion transcript says proactive chat is due, run one turn and queue WS payload."""
    user_id = str(ctx.get("user_id") or "").strip()
    agent_id = str(ctx.get("agent_id") or "").strip()
    chat_id_raw = ctx.get("chat_id")
    if not user_id or not agent_id or chat_id_raw is None:
        return

    async with AsyncSessionLocal() as pre_db:
        r_user = await pre_db.execute(select(User).where(User.id == user_id))
        current_user = r_user.scalar_one_or_none()
        if current_user is None:
            return

        chat = await chat_service.get_or_create_chat_by_agent(
            db=pre_db, user_id=user_id, agent_id=agent_id
        )
        if str(chat.id) != str(chat_id_raw):
            logger.debug(
                "companion_ws_proactive_chat chat_id mismatch ws_conn_id={} ctx={} db_chat_id={}",
                ws_conn_id,
                chat_id_raw,
                chat.id,
            )
            return

        subscription = await subscription_svc.get_user_current_subscription(
            pre_db, user_id
        )
        is_subscribed = bool(subscription)
        model_override = select_chat_model(
            user=current_user, is_subscribed=is_subscribed
        )

        mem_store = companion_chat_service.companion_memory_store_if_ready(
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat.id,
            resolved_chat_model=model_override,
        )
        if mem_store is None:
            return

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
            return

        chat_row_id = chat.id
        chat_row_agent_id = chat.agent_id
        session_id = generate_session_id(str(chat_row_id))
        preset_uid = str(uuid.uuid4())

    ws_implicit = implicit_signal_bundle_from_tc_box(tc_box)
    async with coordinator.turn_lock:
        coordinator.clear_inner_tick_proactive_tool_bg_idle_if_idle()
        if coordinator.inner_tick_proactive_tool_bg_still_running():
            logger.debug(
                "companion_ws_proactive_chat skipped prev_inner_tick_tool_bg ws_conn_id={} user={} agent={}",
                ws_conn_id,
                user_id,
                agent_id,
            )
            return
        companion_turn = await companion_chat_service.run_companion_inner_tick_proactive_chat_turn_for_api(
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat_row_id,
            resolved_chat_model=model_override,
            defer_memory_update=True,
            session_id=session_id,
            background_output_sink=None,
            preset_user_msg_uuid=preset_uid,
            implicit_signal_bundle=ws_implicit,
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
            try:
                await subscription_svc.record_usage(
                    post_db,
                    user_id,
                    "chat",
                    1,
                    extra_data={
                        "agent_id": agent_id,
                        "message_length": 0,
                        "companion_ws_proactive_chat": True,
                    },
                )
            except Exception as e:
                logger.warning(
                    "companion_ws_proactive_chat record_usage failed ws_conn_id={}: {}",
                    ws_conn_id,
                    str(e),
                )

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


async def try_fire_maintenance_inner_tick(
    *,
    delivery: InnerTickDelivery,
    ctx: dict[str, Any],
    subscription_svc: SubscriptionService,
    coordinator: Coordinator,
    ws_conn_id: str,
    tc_box: list[Optional[dict]],
) -> None:
    """If companion transcript says maintenance inner-tick is due, run one MAINTENANCE turn and queue WS."""
    # TODO(tool-bg-idle-starves-user-chat): Foreground often returns tool_bg_only while session
    # tool_bg_idle stays cleared until the bg thread finishes; proactive then holds turn_lock
    # inside run_turn idle wait and queues USER_MESSAGE with no chat reply.
    # https://github.com/NascentCore/inty/issues/3123
    user_id = str(ctx.get("user_id") or "").strip()
    agent_id = str(ctx.get("agent_id") or "").strip()
    chat_id_raw = ctx.get("chat_id")
    if not user_id or not agent_id or chat_id_raw is None:
        return

    async with AsyncSessionLocal() as pre_db:
        r_user = await pre_db.execute(select(User).where(User.id == user_id))
        current_user = r_user.scalar_one_or_none()
        if current_user is None:
            return

        chat = await chat_service.get_or_create_chat_by_agent(
            db=pre_db, user_id=user_id, agent_id=agent_id
        )
        if str(chat.id) != str(chat_id_raw):
            logger.debug(
                "companion_ws_maintenance_inner_tick chat_id mismatch ws_conn_id={} ctx={} db_chat_id={}",
                ws_conn_id,
                chat_id_raw,
                chat.id,
            )
            return

        subscription = await subscription_svc.get_user_current_subscription(
            pre_db, user_id
        )
        is_subscribed = bool(subscription)
        model_override = select_chat_model(
            user=current_user, is_subscribed=is_subscribed
        )

        mem_store = companion_chat_service.companion_memory_store_if_ready(
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat.id,
            resolved_chat_model=model_override,
        )
        if mem_store is None:
            return

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
                poll_seconds=float(
                    feats.companion_ws_proactive_chat_poll_seconds
                ),
            ),
        )
        if remain > 0:
            return

        is_allowed, used_count, daily_limit = (
            await subscription_svc.check_chat_limit(pre_db, current_user)
        )
        if not is_allowed:
            logger.info(
                "companion_ws_maintenance_inner_tick skipped subscription ws_conn_id={} user={} used={} limit={}",
                ws_conn_id,
                user_id,
                used_count,
                daily_limit,
            )
            return

        chat_row_id = chat.id
        chat_row_agent_id = chat.agent_id
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

    async with coordinator.turn_lock:
        if coordinator.inner_tick_maintenance_foreground_pending():
            logger.debug(
                "companion_ws_maintenance_inner_tick skipped prev_inner_tick_pending "
                "ws_conn_id={} user={} agent={}",
                ws_conn_id,
                user_id,
                agent_id,
            )
            return
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
                defer_memory_update=True,
                session_id=session_id,
                background_output_sink=coordinator.background_sink,
                preset_user_msg_uuid=preset_uid,
                implicit_signal_bundle=ws_implicit,
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
            return

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
            try:
                await subscription_svc.record_usage(
                    post_db,
                    user_id,
                    "chat",
                    1,
                    extra_data={
                        "agent_id": agent_id,
                        "message_length": 0,
                        "companion_ws_maintenance_inner_tick": True,
                    },
                )
            except Exception as e:
                logger.warning(
                    "companion_ws_maintenance_inner_tick record_usage failed ws_conn_id={}: {}",
                    ws_conn_id,
                    str(e),
                )

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
    else:
        logger.info(
            "companion_ws_maintenance_inner_tick tool_bg_only ws_conn_id={} user={} agent={} chat_id={}",
            ws_conn_id,
            user_id,
            agent_id,
            chat_row_id,
        )
