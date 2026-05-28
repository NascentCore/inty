"""Connection-level WebSocket transport helpers for companion chat."""

import asyncio
from typing import Any

from fastapi import HTTPException, WebSocketDisconnect
from loguru import logger

from app.core.config import global_config_loaded_from_config_yaml
from app.schemas.chat_websocket import chat_ws_queued_error_dict

def _chat_ws_error_payload_from_http_exception(
    exc: HTTPException, *, agent_id: str
) -> dict[str, Any]:
    detail = exc.detail
    message = detail if isinstance(detail, str) else str(detail)
    ws_extra = getattr(exc, "ws_extra", None)
    return chat_ws_queued_error_dict(
        status_code=exc.status_code,
        message=message,
        agent_id=agent_id,
        ws_extra=ws_extra if isinstance(ws_extra, dict) else None,
    )


# WebSocket: one AsyncSession is bound for the whole connection (Depends(get_async_db)).
# Handlers must not pass that session into asyncio.to_thread or other threads; open a new
# session inside the worker if agentic work runs off the event loop.


def _chat_ws_idle_timeout_seconds() -> float:
    return float(
        global_config_loaded_from_config_yaml.app.features.chat_ws_idle_timeout_seconds
    )


# Starlette ``WebSocket.receive_text`` when ``application_state != CONNECTED`` (race after drop).
_WS_RECEIVE_TEXT_NOT_CONNECTED_MSG: str = (
    'WebSocket is not connected. Need to call "accept" first.'
)


def _is_ws_receive_text_not_connected_runtime_error(exc: BaseException) -> bool:
    return (
        isinstance(exc, RuntimeError)
        and str(exc) == _WS_RECEIVE_TEXT_NOT_CONNECTED_MSG
    )


async def _shutdown_chat_ws_outbound_pump(pump_task: asyncio.Task) -> None:
    """Join ``chat_ws_outbound_pump``; cancel if still running.

    ``WebSocketDisconnect`` after the client has gone is expected during teardown and is logged
    at debug. Other exceptions are logged at error (distinct from normal ``CancelledError``).
    """
    if not pump_task.done():
        pump_task.cancel()
    try:
        await pump_task
    except asyncio.CancelledError:
        pass
    except WebSocketDisconnect:
        logger.debug(
            "chat_ws_outbound_pump task ended: client disconnected during pump teardown"
        )
    except Exception:
        logger.exception(
            "chat_ws_outbound_pump failed (e.g. WebSocket send_json); "
            "distinct from normal CancelledError teardown"
        )
