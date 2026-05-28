"""WebSocket session ``tc_box`` time_context merge and implicit signals."""

from datetime import datetime, timezone
from typing import Optional

from loguru import logger
from pydantic import ValidationError

from app.schemas.chat import ChatCompletionRequest, UserTimeContext
from app.schemas.implicit_signals import ImplicitSignalBundle

def _chat_request_with_merged_ws_time_context(
    request: ChatCompletionRequest,
    ws_session_time_context: Optional[dict],
) -> ChatCompletionRequest:
    """
    单连接上先发送 client_context 时，后续 chat 帧可省略 time_context；
    若请求体已带 user_time_context，以请求为准。
    """
    if not ws_session_time_context:
        return request
    if request.user_time_context is not None:
        return request
    try:
        utc = UserTimeContext.model_validate(ws_session_time_context)
    except ValidationError:
        return request
    return request.model_copy(update={"user_time_context": utc})


def _implicit_signal_bundle_from_ws_tc_box(
    tc_box: list[Optional[dict]],
) -> Optional[ImplicitSignalBundle]:
    """Build companion ``ImplicitSignalBundle`` from WebSocket ``client_context`` cache (``tc_box[0]``)."""
    if not tc_box:
        return None
    raw = tc_box[0]
    if not raw:
        return None
    try:
        utc = UserTimeContext.model_validate(raw)
    except ValidationError as exc:
        logger.warning(
            "chat_ws tc_box time_context invalid error={}",
            str(exc)[:500],
        )
        return None
    return ImplicitSignalBundle(
        client_time=utc,
        user_signed_on=False,
        server_received_at_utc=datetime.now(timezone.utc),
    )
