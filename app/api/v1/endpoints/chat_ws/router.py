"""Companion chat WebSocket route registration only."""

from fastapi import APIRouter, Depends, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.api.utils.logger_route import LoggerRoute
from app.api.v1.endpoints.chat_ws.production_session import run_companion_chat_ws_session
from app.api.v1.endpoints.chat_ws.verify_session import run_companion_chat_ws_verify_session
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
    await run_companion_chat_ws_session(
        websocket, db, subscription_svc, voice_svc
    )


@router.websocket("/ws/verify")
async def chat_completions_websocket_verify(
    websocket: WebSocket,
    db: AsyncSession = Depends(deps.get_async_db),
    subscription_svc: SubscriptionService = Depends(
        deps.get_subscription_service
    ),
):
    """
    Legacy smoke endpoint: same **outbound queue + pump** as ``/ws`` (FIFO business JSON).

    Per chat frame: **one** ``chat.completions`` call with system + user messages only (via
    ``get_chat_openai_client``). No ``Agent`` runtime, no companion pipeline, no chat_history
    persistence. Use to validate transport, queue behavior, and minimal LLM connectivity.
    """
    await run_companion_chat_ws_verify_session(
        websocket, db, subscription_svc
    )
