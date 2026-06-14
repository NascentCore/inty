"""WebSocket downlink deliver context for bootstrap interim materialization."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.chat import ChatCompletionRequest


@dataclass
class WsDownlinkDeliverCtx:
    """Per user-chat turn: materialize bootstrap interim into chat history + WS queue."""

    db: AsyncSession
    agent_id: str
    session_id: str
    request: ChatCompletionRequest
    last_user_text: str
    effective_local_id: str | None
    outbound_queue: asyncio.Queue[Any]
