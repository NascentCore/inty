"""Persist visible inner-tick turns and push channel delivery (WS / Weixin / Telegram)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loguru import logger

from app.core.companion_harness.companion.models import CompanionTurnResult
from app.core.companion_harness.companion.models import (
    user_visible_assistant_text,
)
from app.core.companion_harness.companion.runtime_channel import (
    is_im_runtime_channel,
)
from app.db.session import AsyncSessionLocal
from app.schemas.biz_action import ActionType, BizAction
from app.schemas.chat import ChatCompletionRequest
from app.schemas.chat_websocket import (
    ChatWsCompanionWireMessageMetaData,
    dump_chat_ws_companion_wire_meta,
)
from app.schemas.response import APIResponse
from app.services import chat_history_service
from app.services.agent_status_line import (
    agent_status_line_for_chat_header as _agent_status_line_for_chat_header,
)
from app.services.agentic_companion.inner_tick_delivery import (
    InnerTickDelivery,
    deliver_inner_tick_assistant,
)
from app.services.agentic_companion.ws_turn_support import (
    companion_ai_meta_from_turn_result,
)
from app.services.chat_completion_wire import (
    _normalize_chat_response_content,
    build_companion_ws_completion_data,
)


@dataclass(frozen=True)
class InnerTickVisibleDeliverInput:
    """One user-visible inner-tick round after kernel turn completes."""

    delivery: InnerTickDelivery
    session_id: str
    agent_id: str
    chat_row_agent_id: str
    ws_conn_id: str
    preset_uid: str
    transcript_user_text: str
    companion_turn: CompanionTurnResult
    stub_request: ChatCompletionRequest
    user_wire_meta: ChatWsCompanionWireMessageMetaData
    companion_scheduled_reminder: bool | None
    scheduled_task_id: str | None
    log_label: str
    skip_user_history: bool


async def deliver_visible_inner_tick_turn(
    deliver_input: InnerTickVisibleDeliverInput,
) -> bool:
    """Write chat_history rows and enqueue outbound assistant payload when non-empty.

    Returns True when user-visible assistant text was delivered on the channel.
    """
    if not deliver_input.skip_user_history:
        user_meta = dump_chat_ws_companion_wire_meta(
            deliver_input.user_wire_meta
        )
        await chat_history_service.add_user_message_async(
            deliver_input.session_id,
            deliver_input.transcript_user_text,
            meta_data=user_meta,
        )

    companion_reply = deliver_input.companion_turn.assistant_text
    reply_stripped = user_visible_assistant_text(
        str(companion_reply) if companion_reply is not None else ""
    )
    if reply_stripped is None:
        return False

    companion_ai_meta = companion_ai_meta_from_turn_result(
        deliver_input.companion_turn,
        companion_scheduled_reminder=deliver_input.companion_scheduled_reminder,
        scheduled_task_id=deliver_input.scheduled_task_id,
    )
    ai_message_id = await chat_history_service.add_ai_message_sync_async(
        deliver_input.session_id,
        companion_reply,
        agent_id=deliver_input.chat_row_agent_id,
        meta_data=companion_ai_meta,
    )

    # AgenticLoop already appended this turn's visible rows to the scope
    # OutputQueue; on IM channels the presence output pump owns delivery of
    # agent-initiated rows, so a direct channel send here would duplicate the
    # message. Keep chat_history persistence above, skip the channel push.
    # TODO(#3543): converge App-WS onto the same pump-owned delivery, then
    # dissolve this direct-send path entirely.
    if (
        deliver_input.companion_turn.output_message_ids
        and is_im_runtime_channel(deliver_input.delivery.runtime_channel)
    ):
        logger.info(
            "{} channel send delegated to scope output pump "
            "(output_message_ids={})",
            deliver_input.log_label,
            deliver_input.companion_turn.output_message_ids,
        )
        return True

    async with AsyncSessionLocal() as post_db:
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
                        post_db, deliver_input.session_id
                    )
                )
        except Exception as exc:
            logger.warning(
                "{} latest_message_info failed ws_conn_id={}: {}",
                deliver_input.log_label,
                deliver_input.ws_conn_id,
                exc,
            )

        user_message_id = None
        try:
            user_message_id = (
                await chat_history_service.get_latest_user_message_id(
                    post_db, deliver_input.session_id
                )
            )
        except Exception as exc:
            logger.warning(
                "{} get_latest_user_message_id failed ws_conn_id={}: {}",
                deliver_input.log_label,
                deliver_input.ws_conn_id,
                exc,
            )

        subscription_actions = [
            BizAction(action_type=ActionType.NONE, message=""),
        ]
        completion = build_companion_ws_completion_data(
            response_text_content=response_text_content,
            response_content_parts=response_content_parts,
            last_user_text=deliver_input.transcript_user_text,
            latest_message_info=latest_message_info,
            audio_url=None,
            request=deliver_input.stub_request,
            source_imate_id=None,
            user_message_id=user_message_id,
            subscription_actions=subscription_actions,
            client_local_id=None,
        )
        payload = APIResponse.success(
            data=completion.model_dump(exclude_none=True)
        )
        out: dict[str, Any] = payload.model_dump(exclude_none=True)
        out["agent_id"] = deliver_input.agent_id
        out["status_line"] = await _agent_status_line_for_chat_header(
            post_db, deliver_input.agent_id
        )
        await deliver_inner_tick_assistant(
            deliver_input.delivery,
            ws_payload=out,
            assistant_text=response_text_content,
        )
    return True
