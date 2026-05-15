"""Shared logic for TTS on an existing persisted chat row (REST on-demand voice + companion tool)."""

from __future__ import annotations

from typing import Any, Literal

from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import AuthType
from app.services import agent_service, chat_history_service, chat_service
from app.services.chat_service import generate_session_id
from app.services.subscription_service import SubscriptionService
from app.services.voice_service import (
    VoiceService,
    get_voice_message_narration_mode_from_agent_settings,
)


class ChatMessageVoiceSynthesisResult(BaseModel):
    """Outcome of attempting TTS + optional chat_history audio_url update for one message."""

    outcome: Literal[
        "success",
        "agent_not_found",
        "chat_not_found",
        "message_not_found",
        "chat_id_mismatch",
        "voice_failed_limit_guest",
        "voice_failed_limit_logged_in",
        "voice_failed_other",
    ]
    session_id: str = ""
    message_id: str = ""
    language: str = "zh"
    audio_url: str = ""
    gcs_url: str = ""
    gcs_http_url: str = ""
    audio_duration: float = Field(default=0.0, ge=0.0)
    resolved_voice_id: str | None = None
    used_count: int | None = None
    limit: int | None = None


async def synthesize_voice_for_persisted_chat_message(
    *,
    db: AsyncSession,
    current_user: Any,
    agent_id: str,
    message_id: str,
    language: str,
    voice_svc: VoiceService,
    subscription_svc: SubscriptionService,
    expected_chat_id: str | None = None,
) -> ChatMessageVoiceSynthesisResult:
    """
    Load message text from chat_history, synthesize audio, persist ``audio_url`` on success.

    ``expected_chat_id``: when set (e.g. from companion ``context.json``), the resolved chat's
    primary key must match; otherwise returns ``chat_id_mismatch`` without generating audio.
    """
    lang = (language or "zh").strip() or "zh"
    mid = (message_id or "").strip()
    aid = (agent_id or "").strip()
    base = ChatMessageVoiceSynthesisResult(
        outcome="voice_failed_other", message_id=mid, language=lang
    )
    if not mid or not aid:
        return base.model_copy(update={"outcome": "message_not_found"})

    agent_data = await agent_service.get_agent_for_chat(db, agent_id=aid)
    if not agent_data:
        return base.model_copy(update={"outcome": "agent_not_found"})

    chat = await chat_service.get_chat_by_user_and_agent(
        db=db, user_id=current_user.id, agent_id=aid
    )
    if not chat:
        return base.model_copy(update={"outcome": "chat_not_found"})

    exp = (expected_chat_id or "").strip()
    if exp and str(chat.id).strip() != exp:
        return base.model_copy(update={"outcome": "chat_id_mismatch"})

    session_id = generate_session_id(chat.id)
    message_content = await chat_history_service.get_message_content(
        db=db, session_id=session_id, message_id=mid
    )
    if not message_content:
        return base.model_copy(
            update={"outcome": "message_not_found", "session_id": session_id}
        )

    selected_chat_voice_id = (
        chat.settings.voice_id if getattr(chat, "settings", None) else None
    )
    agent_voice_id = agent_data.get("voice_id")
    resolved_voice_id = selected_chat_voice_id or agent_voice_id
    voice_message_narration_mode = get_voice_message_narration_mode_from_agent_settings(
        agent_data.get("settings")
    )

    voice_result = await voice_svc.generate_voice(
        text=message_content,
        voice_id=resolved_voice_id,
        language=lang,
        db=db,
        agent_gender=agent_data.get("gender"),
        user=current_user,
        voice_message_narration_mode=voice_message_narration_mode,
    )

    if not voice_result:
        is_allowed, used_count, limit = await subscription_svc.check_voice_generation_limit(
            db, current_user
        )
        if not is_allowed:
            if current_user.auth_type == AuthType.GUEST:
                return base.model_copy(
                    update={
                        "outcome": "voice_failed_limit_guest",
                        "session_id": session_id,
                        "used_count": used_count,
                        "limit": limit,
                    }
                )
            return base.model_copy(
                update={
                    "outcome": "voice_failed_limit_logged_in",
                    "session_id": session_id,
                    "used_count": used_count,
                    "limit": limit,
                }
            )
        return base.model_copy(update={"outcome": "voice_failed_other", "session_id": session_id})

    audio_url = voice_result.gcs_http_url
    audio_duration = voice_result.duration_seconds
    logger.debug(
        "synthesize_voice_for_persisted_chat_message ok session_id={} message_id={} audio_url={}",
        session_id,
        mid,
        audio_url,
    )

    try:
        await chat_history_service.update_message_audio_url(
            db=db,
            session_id=session_id,
            message_id=mid,
            audio_url=audio_url,
            audio_duration=audio_duration,
        )
    except Exception as e:
        logger.warning(
            "update_message_audio_url failed session_id={} id={}: {}", session_id, mid, e
        )

    return ChatMessageVoiceSynthesisResult(
        outcome="success",
        session_id=session_id,
        message_id=mid,
        language=lang,
        audio_url=audio_url,
        gcs_url=voice_result.gcs_url,
        gcs_http_url=voice_result.gcs_http_url,
        audio_duration=audio_duration,
        resolved_voice_id=resolved_voice_id,
    )
