"""Ops product API: Telegram onboard bot metadata for GET /telegram QR page."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import global_config_loaded_from_config_yaml
from app.external_services.telegram_bot_api import TelegramBotApi
from app.schemas.response import APIResponse
from app.utils.config import resolved_telegram_bot_token

router = APIRouter(prefix="/telegram", include_in_schema=False)


class TelegramBotInfoData(BaseModel):
    bot_id: int = Field(description="Telegram bot numeric id from getMe")
    bot_username: str = Field(description="Bot @username without @ prefix")


@router.get("/bot-info", response_model=APIResponse[TelegramBotInfoData])
async def telegram_bot_info() -> APIResponse[TelegramBotInfoData]:
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
