"""Tagged items for repl-client message-queue / IO (tools/inty_v2_repl only)."""

from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict


class ReplDownlinkAssistant(TypedDict):
    """Server pushed a successful chat completion frame."""

    kind: Literal["assistant"]
    text: str
    raw: dict[str, Any]
    meta_data: dict[str, Any]
    audio_url: NotRequired[str]


class ReplDownlinkWsError(TypedDict):
    """Server returned an API error JSON frame on the chat WebSocket."""

    kind: Literal["ws_error"]
    code: int
    message: str
    raw: dict[str, Any]


ReplDownlinkItem = ReplDownlinkAssistant | ReplDownlinkWsError
