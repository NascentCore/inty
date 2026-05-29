"""Bootstrap interim downlink delivery for companion chat WebSocket sessions."""

from __future__ import annotations

from loguru import logger

from app.core.companion_harness.companion.websocket_coordinator import (
    BootstrapInterimQueued,
    CompanionWebSocketCoordinator,
)
from app.schemas.biz_action import ActionType, BizAction
from app.schemas.chat_websocket import (
    ChatWsCompanionWireMessageMetaData,
    dump_chat_ws_companion_wire_meta,
)
from app.schemas.response import APIResponse
from app.services import chat_history_service
from app.api.v1.endpoints.chat import (
    _agent_status_line_for_chat_header,
    _build_chat_response,
)

async def _deliver_bootstrap_interim_queued(
    queued: BootstrapInterimQueued,
) -> None:
    """Materialize one bootstrap sync tool-loop round into chat history + WS outbound."""
    ev = queued.ev
    ctx = queued.ctx
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
        ctx.session_id,
        ev.text,
        agent_id=ctx.agent_id,
        meta_data=meta_data,
    )
    latest_message_info = None
    try:
        if ai_message_id is not None:
            latest_message_info = (
                await chat_history_service.get_ai_message_info_by_id(
                    ctx.db, ai_message_id
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
        ctx.last_user_text,
        latest_message_info,
        None,
        ctx.request,
        source_imate_id=ctx.request.target_imate_id,
        user_message_id=None,
        subscription_actions=subscription_actions,
        client_local_id=ctx.effective_local_id,
    )
    payload = APIResponse.success(data=data)
    out = payload.model_dump(exclude_none=True)
    out["agent_id"] = ctx.agent_id
    out["status_line"] = await _agent_status_line_for_chat_header(
        ctx.db, ctx.agent_id
    )
    await ctx.outbound_queue.put(out)

async def _companion_ws_bootstrap_interim_consumer(
    companion_ws: CompanionWebSocketCoordinator,
) -> None:
    """Drain ``bootstrap_interim_queued_events`` for the lifetime of one ``/api/v1/chat/ws`` session."""
    while True:
        queued = await companion_ws.bootstrap_interim_queued_events.get()
        try:
            await _deliver_bootstrap_interim_queued(queued)
        except Exception:
            logger.exception("companion_ws bootstrap_interim deliver failed")
