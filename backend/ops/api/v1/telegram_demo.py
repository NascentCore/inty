"""Ops-only API: Telegram demo bot metadata and debug bindings."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import global_config_loaded_from_config_yaml
from app.external_services.telegram_bot_api import TelegramBotApi
from app.schemas.response import APIResponse
from app.utils.config import resolved_telegram_bot_token
from backend.ops.telegram_demo.persistence import list_bindings

router = APIRouter(prefix="/telegram-demo", tags=["telegram-demo"])


class TelegramBotInfoData(BaseModel):
    bot_id: int = Field(description="Telegram bot numeric id from getMe")
    bot_username: str = Field(description="Bot @username without @ prefix")


class TelegramBindingRow(BaseModel):
    telegram_chat_id: str = Field(description="Telegram DM chat id")
    user_id: str = Field(description="Inty guest user id")
    agent_id: str = Field(description="Companion agent id")
    chat_id: str = Field(description="Inty chat id")


class TelegramBindingsData(BaseModel):
    count: int = Field(description="Number of persisted bindings")
    bindings: list[TelegramBindingRow] = Field(description="Active binding rows")


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
    """Debug: list Postgres-persisted Telegram demo bindings (no secrets)."""
    rows = await list_bindings()
    return APIResponse.success(
        data=TelegramBindingsData(
            count=len(rows),
            bindings=[
                TelegramBindingRow(
                    telegram_chat_id=row.telegram_chat_id,
                    user_id=row.user_id,
                    agent_id=row.agent_id,
                    chat_id=row.chat_id,
                )
                for row in rows
            ],
        )
    )
