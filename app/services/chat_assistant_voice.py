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
from app.services.voice_service import (
    VoiceService,
    get_voice_message_narration_mode_from_agent_settings,
)
from app.utils.timing import log_time


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
    if use_companion and str(companion_reply_modality or "").strip() == "voice_message":
        tts_text = (companion_voice_script or "").strip() or (
            response_text_content or ""
        ).strip()
    else:
        tts_text = (response_text_content or "").strip()
    if not tts_text:
        return audio_url, audio_duration
    resolved_voice_id = chat_voice_id or agent_voice_id
    voice_message_narration_mode = get_voice_message_narration_mode_from_agent_settings(
        agent_settings
    )
    voice_result = None
    try:
        with log_time(
            f"语音生成: voice_id={resolved_voice_id}, text_length={len(tts_text)}, language={language}"
        ):
            is_allowed, used_count, limit = await voice_svc.check_quota(
                db=db, user=current_user
            )
            if not is_allowed:
                logger.warning(
                    "用户 {} 已达到语音生成限制: {}/{}，聊天文本正常返回",
                    current_user.id,
                    used_count,
                    limit,
                )
                return audio_url, audio_duration

            synthesis_voice_id, synthesis_text = (
                voice_svc.prepare_synthesis_voice_id_and_text(
                    tts_text,
                    resolved_voice_id,
                    agent_gender,
                )
            )
            if not synthesis_text.strip() or not synthesis_voice_id:
                return audio_url, audio_duration

            provider_selected = (
                TTS_PROVIDER_GEMINI
                if is_gemini_voice(synthesis_voice_id)
                else TTS_PROVIDER_ELEVENLABS
            )
            model, model_source = await voice_svc.resolve_generation_model(
                provider_selected=provider_selected,
                requested_model=None,
                db=db,
                user=current_user,
            )
            gemini_source_model: Optional[str] = None
            if (
                provider_selected != TTS_PROVIDER_GEMINI
                and global_config_loaded_from_config_yaml.tts.enable_gemini_tts_then_elevenlabs_voice_changer_for_imate
            ):
                gemini_source_model, _ = await voice_svc.resolve_generation_model(
                    provider_selected=TTS_PROVIDER_GEMINI,
                    requested_model=None,
                    db=db,
                    user=current_user,
                )

            cached = await voice_svc.lookup_cached_voice(
                db=db,
                text=synthesis_text,
                voice_id=synthesis_voice_id,
                model=model,
                language=language,
            )
            if cached:
                await voice_svc.record_voice_usage(
                    db=db,
                    user=current_user,
                    text_length=len(synthesis_text),
                    voice_id=synthesis_voice_id,
                    cached=True,
                )
                voice_result = cached
            else:
                voice_result = await voice_svc.generate_voice_no_quota_limit_check(
                    text=tts_text,
                    voice_id=resolved_voice_id,
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
                        user=current_user,
                        text_length=len(synthesis_text),
                        voice_id=synthesis_voice_id,
                        cached=False,
                    )

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
