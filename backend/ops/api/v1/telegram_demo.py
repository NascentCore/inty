"""Ops debug API: Telegram binding rows (local/dev when app.debug)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.companion_harness.agent_channel.gateway import (
    GatewayKind,
)
from app.schemas.response import APIResponse
from app.services.agentic_channel.endpoints import list_endpoints_for_channel

router = APIRouter(prefix="/telegram-demo", tags=["telegram-demo"])


class TelegramBindingRow(BaseModel):
    channel_address: str = Field(description="Telegram DM chat id")
    channel_user_id: str = Field(description="Telegram User id")
    user_id: str = Field(description="Inty guest user id")
    agent_id: str = Field(description="Companion agent id")


class TelegramBindingsData(BaseModel):
    count: int = Field(description="Number of persisted bindings")
    bindings: list[TelegramBindingRow] = Field(
        description="Active binding rows"
    )


@router.get(
    "/bindings",
    response_model=APIResponse[TelegramBindingsData],
    include_in_schema=False,
)
async def telegram_demo_bindings() -> APIResponse[TelegramBindingsData]:
    """Debug: list Postgres-persisted Telegram agent_channel endpoints.

    TODO(telegram-launch-reciprocity-metrics): Add bootstrap / proactive / reciprocity flags
    per binding for launch north-star — #3535 (epic #3531).
    """
    rows = await list_endpoints_for_channel(channel=GatewayKind.TELEGRAM)
    return APIResponse.success(
        data=TelegramBindingsData(
            count=len(rows),
            bindings=[
                TelegramBindingRow(
                    channel_address=row.channel_address,
                    channel_user_id=row.channel_user_id,
                    user_id=row.user_id,
                    agent_id=row.agent_id,
                )
                for row in rows
            ],
        )
    )
