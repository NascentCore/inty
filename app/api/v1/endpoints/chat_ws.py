"""Companion chat WebSocket endpoint declarations."""

from fastapi import APIRouter, Depends, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.api.utils.logger_route import LoggerRoute
from app.services.chat_websocket.handlers import (
    run_chat_completions_websocket,
    run_chat_completions_websocket_verify,
)
from app.services.subscription_service import SubscriptionService
from app.services.voice_service import VoiceService

router = APIRouter(route_class=LoggerRoute)


@router.websocket("/ws")
async def chat_completions_websocket(
    websocket: WebSocket,
    db: AsyncSession = Depends(deps.get_async_db),
    subscription_svc: SubscriptionService = Depends(
        deps.get_subscription_service
    ),
    voice_svc: VoiceService = Depends(deps.get_voice_service),
):
    await run_chat_completions_websocket(
        websocket=websocket,
        db=db,
        subscription_svc=subscription_svc,
        voice_svc=voice_svc,
    )


@router.websocket("/ws/verify")
async def chat_completions_websocket_verify(
    websocket: WebSocket,
    db: AsyncSession = Depends(deps.get_async_db),
    subscription_svc: SubscriptionService = Depends(
        deps.get_subscription_service
    ),
):
    await run_chat_completions_websocket_verify(
        websocket=websocket,
        db=db,
        subscription_svc=subscription_svc,
    )
