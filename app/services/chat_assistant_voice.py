from __future__ import annotations

from typing import Any, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import global_config_loaded_from_config_yaml
from app.core.voice.tts_api import (
    TTS_PROVIDER_ELEVENLABS,
    TTS_PROVIDER_GEMINI,
    is_gemini_voice,
)
from app.services import chat_history_service
from app.services.global_services import subscription_service
from app.services.voice_cache_service import voice_cache_service
from app.services.voice_service import (
    VoiceGenerationResult,
    VoiceService,
    get_voice_message_narration_mode_from_agent_settings,
)
from app.utils.timing import log_time


async def produce_voice_for_user(
    *,
    voice_svc: VoiceService,
    db: AsyncSession,
    user: Any,
    text: str,
    voice_id: Optional[str],
    language: str,
    agent_gender: Optional[str],
    voice_message_narration_mode: Optional[Any],
) -> tuple[Optional[VoiceGenerationResult], bool, int, int]:
    """
    用户上下文下的语音生成编排：配额 → 模型 → 缓存 → TTS → 记用量。

    Returns:
        (result, is_allowed, used_count, limit)
    """
    (
        is_allowed,
        used_count,
        limit,
    ) = await subscription_service.check_voice_generation_limit(db, user)
    if not is_allowed:
        logger.warning(
            "用户 {} 已达到语音生成限制: {}/{}",
            user.id,
            used_count,
            limit,
        )
        return None, is_allowed, used_count, limit

    synthesis_voice_id, synthesis_text = (
        voice_svc.prepare_synthesis_voice_id_and_text(
            text,
            voice_id,
            agent_gender,
        )
    )
    if not synthesis_text.strip() or not synthesis_voice_id:
        return None, is_allowed, used_count, limit

    provider_selected = (
        TTS_PROVIDER_GEMINI
        if is_gemini_voice(synthesis_voice_id)
        else TTS_PROVIDER_ELEVENLABS
    )
    model, model_source = await voice_svc.resolve_tts_model(
        provider_selected=provider_selected,
        db=db,
        user=user,
    )
    gemini_source_model: Optional[str] = None
    if (
        provider_selected != TTS_PROVIDER_GEMINI
        and global_config_loaded_from_config_yaml.tts.enable_gemini_tts_then_elevenlabs_voice_changer_for_imate
    ):
        gemini_source_model, _ = await voice_svc.resolve_tts_model(
            provider_selected=TTS_PROVIDER_GEMINI,
            db=db,
            user=user,
        )

    cached = await voice_cache_service.get_cached_voice(
        db,
        synthesis_text,
        synthesis_voice_id,
        model,
        language,
    )
    if cached:
        await voice_svc.record_voice_usage(
            db=db,
            user=user,
            text_length=len(synthesis_text),
            voice_id=synthesis_voice_id,
            cached=True,
        )
        return cached, is_allowed, used_count, limit

    voice_result = await voice_svc.generate_voice_no_quota_limit_check(
        text=text,
        voice_id=voice_id,
        language=language,
        model=model,
        model_source=model_source,
        agent_gender=agent_gender,
        voice_message_narration_mode=voice_message_narration_mode,
        gemini_source_model=gemini_source_model,
    )
    if voice_result:
        await voice_svc.record_voice_usage(
            db=db,
            user=user,
            text_length=len(synthesis_text),
            voice_id=synthesis_voice_id,
            cached=False,
        )
    return voice_result, is_allowed, used_count, limit


async def synthesize_chat_assistant_audio(
    *,
    db: AsyncSession,
    session_id: str,
    ai_message_id: Optional[int],
    voice_enabled: bool,
    chat_voice_id: Optional[str],
    agent_voice_id: Optional[str],
    agent_gender: Optional[str],
    agent_settings: Any,
    language: str,
    current_user: Any,
    voice_svc: VoiceService,
    response_text_content: str,
    use_companion: bool,
    companion_reply_modality: str,
    companion_voice_script: str,
) -> tuple[Optional[str], Optional[float]]:
    audio_url: Optional[str] = None
    audio_duration: Optional[float] = None
    if not voice_enabled:
        return audio_url, audio_duration
    if (
        use_companion
        and str(companion_reply_modality or "").strip() == "voice_message"
    ):
        return audio_url, audio_duration
    else:
        tts_text = (response_text_content or "").strip()
    if not tts_text:
        return audio_url, audio_duration
    resolved_voice_id = chat_voice_id or agent_voice_id
    voice_message_narration_mode = (
        get_voice_message_narration_mode_from_agent_settings(agent_settings)
    )
    voice_result = None
    try:
        with log_time(
            f"语音生成: voice_id={resolved_voice_id}, text_length={len(tts_text)}, language={language}"
        ):
            voice_result, is_allowed, used_count, limit = (
                await produce_voice_for_user(
                    voice_svc=voice_svc,
                    db=db,
                    user=current_user,
                    text=tts_text,
                    voice_id=resolved_voice_id,
                    language=language,
                    agent_gender=agent_gender,
                    voice_message_narration_mode=voice_message_narration_mode,
                )
            )
            if not is_allowed:
                logger.warning(
                    "用户 {} 已达到语音生成限制: {}/{}，聊天文本正常返回",
                    current_user.id,
                    used_count,
                    limit,
                )
                return audio_url, audio_duration

        if voice_result:
            audio_url, audio_duration = voice_result
        else:
            logger.warning(
                "用户 {} 语音生成失败，聊天文本正常返回",
                current_user.id,
            )
    except Exception as e:
        logger.error(f"语音生成失败: {str(e)}")
        logger.exception("语音生成异常详细信息:")
    if audio_url and ai_message_id is not None:
        try:
            await chat_history_service.update_message_audio_url(
                db,
                session_id,
                str(ai_message_id),
                audio_url,
                audio_duration,
            )
        except Exception as e:
            logger.warning(f"持久化 assistant audio_url 失败: {e}")
    return audio_url, audio_duration
