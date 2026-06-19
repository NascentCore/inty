"""Ops-only API: Telegram demo bot metadata and debug bindings."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
)
from app.core.config import global_config_loaded_from_config_yaml
from app.external_services.telegram_bot_api import TelegramBotApi
from app.schemas.response import APIResponse
from app.utils.config import resolved_telegram_bot_token
from app.services.agentic_channel.endpoints import list_endpoints_for_channel

router = APIRouter(prefix="/telegram-demo", tags=["telegram-demo"])


class TelegramBotInfoData(BaseModel):
    bot_id: int = Field(description="Telegram bot numeric id from getMe")
    bot_username: str = Field(description="Bot @username without @ prefix")


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


@router.get("/bot-info", response_model=APIResponse[TelegramBotInfoData])
async def telegram_demo_bot_info() -> APIResponse[TelegramBotInfoData]:
    token = resolved_telegram_bot_token(
        global_config_loaded_from_config_yaml.agent
    )
    if not token:
        raise HTTPException(
            status_code=503,
            detail="agent.channels.telegram.bot_token is not configured",
        )
    api = TelegramBotApi(bot_token=token)
    try:
        me = api.get_me()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return APIResponse.success(
        data=TelegramBotInfoData(
            bot_id=me.bot_id,
            bot_username=me.username,
        )
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
    rows = await list_endpoints_for_channel(
        channel=CompanionRuntimeChannel.TELEGRAM
    )
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
