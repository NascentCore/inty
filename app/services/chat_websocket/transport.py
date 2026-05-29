"""Transport helpers for chat WebSocket sessions."""

from __future__ import annotations

import asyncio
import uuid

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from app.core.config import global_config_loaded_from_config_yaml

def _chat_ws_idle_timeout_seconds() -> float:
    return float(
        global_config_loaded_from_config_yaml.app.features.chat_ws_idle_timeout_seconds
    )


# Starlette ``WebSocket.receive_text`` when ``application_state != CONNECTED`` (race after drop).
_WS_RECEIVE_TEXT_NOT_CONNECTED_MSG: str = (
    'WebSocket is not connected. Need to call "accept" first.'
)

# Starlette ``WebSocket.receive_text`` when ``application_state != CONNECTED`` (race after drop).
_WS_RECEIVE_TEXT_NOT_CONNECTED_MSG: str = (
    'WebSocket is not connected. Need to call "accept" first.'
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

def _resolve_ws_conn_id_from_websocket(websocket: WebSocket) -> str:
    """Prefer client ``ws_conn_id`` query (RFC4122 UUID); else server-generated; invalid query falls back."""
    raw = (websocket.query_params.get("ws_conn_id") or "").strip()
    if not raw:
        return str(uuid.uuid4())
    try:
        return str(uuid.UUID(raw))
    except ValueError:
        generated = str(uuid.uuid4())
        logger.info(
            "chat_ws ws_conn_id_query_invalid using_generated ws_conn_id={} rejected_query={!r}",
            generated,
            raw[:200],
        )
        return generated
