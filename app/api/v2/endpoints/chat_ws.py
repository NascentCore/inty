"""
CREATED_BY_AGENT

WebSocket Chat（双向长连接）：
- 客户端可在 AI 流式输出中发送 `barge_in`（抢话）事件
- 服务端取消当前生成，并在下一轮注入“被打断”提示词以模拟真实对话
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.api import deps
from app.api.utils.logger_route import LoggerRoute
from app.services import chat_service
from app.services.chat_service import generate_session_id
from app.services.realtime_chat_service import realtime_chat_service

router = APIRouter(prefix="/chat", route_class=LoggerRoute)


def _get_event_type(payload: Any) -> Optional[str]:
    if isinstance(payload, dict):
        t = payload.get("type")
        return str(t) if t is not None else None
    return None


@router.websocket("/ws/{agent_id}")
async def chat_ws(
    websocket: WebSocket,
    agent_id: str,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: schemas.User = Depends(deps.get_current_active_user_ws),
):
    """
    协议（客户端 -> 服务端）：
    - `{"type":"user_message","message":"...","client_message_id":"optional"}`
    - `{"type":"barge_in","reason":"optional"}`

    协议（服务端 -> 客户端）：
    - `ack / assistant_delta / assistant_end / assistant_interrupted / error`
    """
    await websocket.accept()

    chat = await chat_service.get_or_create_chat_by_agent(
        db=db, user_id=current_user.id, agent_id=agent_id
    )
    session_id = generate_session_id(chat.id)
    connection_id = await realtime_chat_service.connect(session_id, websocket)

    await websocket.send_json(
        {
            "type": "connected",
            "chat_id": chat.id,
            "session_id": session_id,
            "agent_id": agent_id,
            "user_id": current_user.id,
        }
    )

    try:
        while True:
            payload = await websocket.receive_json()
            event_type = _get_event_type(payload)
            if event_type == "barge_in":
                await realtime_chat_service.interrupt(
                    session_id, reason=str(payload.get("reason") or "barge_in")
                )
                continue

            if event_type == "user_message":
                message = str(payload.get("message") or "").strip()
                if not message:
                    await websocket.send_json(
                        {"type": "error", "error": "bad_request", "message": "empty message"}
                    )
                    continue
                client_message_id = payload.get("client_message_id")
                await realtime_chat_service.handle_user_message(
                    db=db,
                    current_user=current_user,
                    agent_id=agent_id,
                    message=message,
                    client_message_id=str(client_message_id)
                    if client_message_id is not None
                    else None,
                )
                continue

            await websocket.send_json(
                {
                    "type": "error",
                    "error": "bad_request",
                    "message": f"unknown event type: {event_type}",
                }
            )

    except WebSocketDisconnect:
        return
    except Exception as e:
        logger.error(f"chat ws error: {str(e)}")
    finally:
        await realtime_chat_service.disconnect(session_id, connection_id)

