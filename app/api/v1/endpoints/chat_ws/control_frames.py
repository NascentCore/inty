"""Ping and client_context control frames (direct WebSocket, not outbound queue)."""

from typing import Any, Optional

from fastapi import WebSocket
from pydantic import ValidationError

from app.schemas.chat import UserTimeContext
from app.schemas.chat_websocket import ChatWsClientContextAckFrame, ChatWsPongFrame

async def _handle_chat_websocket_control_json(
    websocket: WebSocket,
    data: Any,
    tc_box: list[Optional[dict]],
) -> bool:
    """
    Handle ping / client_context on chat WebSockets. tc_box is a length-1 list holding the
    session's last validated time_context dict (or None). Returns True if the frame was consumed.

    **Transport vs logical channel:** control frames (ping/pong, client_context_ack) are answered
    directly on the WebSocket. Proactive chat inner-tick coords are set by ``user_signed_on`` (see
    ``_try_handle_ws_user_signed_on_frame``) and refreshed on each successful WebSocket companion
    chat turn (``_agent_chat_ws_completions_impl``). They are independent of the connection-level outbound queue used
    for assistant/business JSON. Intentionally so: the WebSocket sits *below* the repl/client
    logical session with the agent; control traffic only confirms link/time-context at the wire layer,
    not the agent dialogue FIFO (which is serialized via ``outbound_queue`` + pump).
    """
    if not isinstance(data, dict):
        return False
    msg_type = data.get("type")
    if msg_type == "ping":
        await websocket.send_json(ChatWsPongFrame().model_dump())
        return True
    if msg_type != "client_context":
        return False
    tc_raw = data.get("time_context")
    if not isinstance(tc_raw, dict):
        await websocket.send_json(
            ChatWsClientContextAckFrame(ok=False).model_dump()
        )
        return True
    try:
        validated = UserTimeContext.model_validate(tc_raw)
        dumped = validated.model_dump(exclude_none=True)
        tc_box[0] = dumped if dumped else None
        await websocket.send_json(
            ChatWsClientContextAckFrame(ok=True).model_dump()
        )
    except ValidationError:
        await websocket.send_json(
            ChatWsClientContextAckFrame(ok=False).model_dump()
        )
    return True
