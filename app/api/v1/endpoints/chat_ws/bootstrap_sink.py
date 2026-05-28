"""Bootstrap interim tool-round output onto the WebSocket outbound queue."""

import asyncio
from typing import Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.chat import _agent_status_line_for_chat_header, _build_chat_response
from app.core.companion_harness.companion.turn_routes import (
    BootstrapInterimOutput,
    BootstrapInterimOutputSink,
)
from app.schemas.biz_action import ActionType, BizAction
from app.schemas.chat import ChatCompletionRequest
from app.schemas.chat_websocket import (
    ChatWsCompanionWireMessageMetaData,
    dump_chat_ws_companion_wire_meta,
)
from app.schemas.response import APIResponse
from app.services import chat_history_service
from app.services.ws_session_messages import WsOutboundPayload

def _bootstrap_interim_output_sink_for_ws(
    *,
    db: AsyncSession,
    agent_id: str,
    session_id: str,
    request: ChatCompletionRequest,
    last_user_text: str,
    effective_local_id: Optional[str],
    ws_outbound_queue: asyncio.Queue[WsOutboundPayload],
) -> BootstrapInterimOutputSink:
    """Push one bootstrap sync tool-loop assistant round onto the WS outbound queue."""

    async def _sink(ev: BootstrapInterimOutput) -> None:
        meta_data = dump_chat_ws_companion_wire_meta(
            ChatWsCompanionWireMessageMetaData(
                source="bootstrap_tool_round",
                trace_id=ev.trace_id or None,
                user_msg_uuid=ev.user_msg_uuid or None,
                assistant_msg_uuid=ev.assistant_msg_uuid or None,
                langsmith_trace_id=ev.langsmith_trace_id or None,
                langsmith_run_id=ev.langsmith_run_id or None,
                bootstrap_round_index=ev.round_index,
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
            logger.warning(
                "bootstrap_interim get_ai_message_info_by_id failed: {}", e
            )
        subscription_actions = [
            BizAction(action_type=ActionType.NONE, message=""),
        ]
        data = _build_chat_response(
            ev.text,
            None,
            last_user_text,
            latest_message_info,
            None,
            request,
            source_imate_id=request.target_imate_id,
            user_message_id=None,
            subscription_actions=subscription_actions,
            client_local_id=effective_local_id,
        )
        payload = APIResponse.success(data=data)
        out = payload.model_dump(exclude_none=True)
        out["agent_id"] = agent_id
        out["status_line"] = await _agent_status_line_for_chat_header(
            db, agent_id
        )
        await ws_outbound_queue.put(out)

    return _sink
