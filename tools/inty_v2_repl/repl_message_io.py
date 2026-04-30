"""Repl terminal IO facade: drain server downlink queue with tagged messages."""

from __future__ import annotations

from .backend_chat_ws import BackendChatWsBridge
from .repl_session_messages import ReplDownlinkItem


def pop_downlink_item(bridge: BackendChatWsBridge) -> ReplDownlinkItem | None:
    """Non-blocking: map ``BackendChatWsBridge.try_pop_queued_chat`` to tagged items."""
    text, err, meta = bridge.try_pop_queued_chat()
    if text is not None:
        return {"kind": "assistant", "text": text, "raw": {}, "meta_data": meta}
    if err is not None:
        code, message = err
        return {
            "kind": "ws_error",
            "code": code,
            "message": message,
            "raw": {},
        }
    return None


def format_ws_error_banner(code: int, message: str, *, wall_ts: str) -> str:
    return f"[{wall_ts}] chat-ws-error sideband code={code} message={message!r}"
