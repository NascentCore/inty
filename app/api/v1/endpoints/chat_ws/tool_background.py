"""Companion tool-background completion payloads for WebSocket outbound queue."""

from typing import Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.chat import (
    _agent_status_line_for_chat_header,
    _build_chat_response,
)
from app.core.companion_harness.tools.image_gate import generated_image_meta_from_index_slice
from app.core.companion_harness.tools.tool_background import ToolOutputEvent
from app.schemas.biz_action import ActionType, BizAction
from app.schemas.chat import ChatCompletionRequest
from app.schemas.chat_websocket import (
    ChatWsCompanionWireMessageMetaData,
    dump_chat_ws_companion_wire_meta,
)
from app.schemas.response import APIResponse
from app.services import chat_history_service
from app.services.ws_session_messages import WsOutboundPayload

async def _build_companion_tool_background_ws_payload(
    *,
    db: AsyncSession,
    agent_id: str,
    session_id: str,
    ev: ToolOutputEvent,
    request: ChatCompletionRequest,
    effective_local_id: Optional[str],
    foreground_user_message_id: Optional[int] = None,
) -> WsOutboundPayload:
    gi = generated_image_meta_from_index_slice(
        ev.memory_store, ev.image_asset_baseline
    )
    tb_paths: list[str] | None = (
        list(ev.local_image_paths) if ev.local_image_paths else None
    )
    sig = ev.significance_perception if ev.significance_perception else None
    meta_data = dump_chat_ws_companion_wire_meta(
        ChatWsCompanionWireMessageMetaData(
            source="tool_bg",
            trace_id=ev.trace_id or None,
            reply_to_user_msg_uuid=ev.user_msg_uuid or None,
            tool_bg_output_to_user=ev.output_to_user,
            tool_bg_generation_deliver=ev.generation_deliver,
            langsmith_trace_id=ev.langsmith_trace_id or None,
            langsmith_run_id=ev.langsmith_run_id or None,
            generated_image=gi or None,
            tool_bg_local_image_paths=tb_paths,
            significance_perception=sig,
            inner_tick_activity=ev.inner_tick_activity,
        )
    )
    ai_message_id = await chat_history_service.add_ai_message_sync_async(
        session_id,
        ev.text,
        agent_id=agent_id,
        meta_data=meta_data,
    )
    latest_message_info = None
    try:
        if ai_message_id is not None:
            latest_message_info = (
                await chat_history_service.get_ai_message_info_by_id(
                    db, ai_message_id
                )
            )
    except Exception as e:
        logger.warning(f"tool_bg get_ai_message_info_by_id failed: {e}")
    user_message_id = foreground_user_message_id
    if user_message_id is None:
        try:
            user_message_id = (
                await chat_history_service.get_latest_user_message_id(
                    db, session_id
                )
            )
        except Exception as e:
            logger.warning(f"tool_bg get_latest_user_message_id failed: {e}")
    subscription_actions = [
        BizAction(action_type=ActionType.NONE, message=""),
    ]
    data = _build_chat_response(
        ev.text,
        None,
        "",
        latest_message_info,
        None,
        request,
        source_imate_id=request.target_imate_id,
        user_message_id=user_message_id,
        subscription_actions=subscription_actions,
        client_local_id=effective_local_id,
    )
    payload = APIResponse.success(data=data)
    out = payload.model_dump(exclude_none=True)
    out["agent_id"] = agent_id
    out["status_line"] = await _agent_status_line_for_chat_header(db, agent_id)
    return out
