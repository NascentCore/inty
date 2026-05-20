"""
语音生成服务
集成 ElevenLabs 和 Gemini TTS API 进行文本转语音
"""

import asyncio
import hashlib
import io
import re
import wave
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional, Tuple

from langsmith.run_helpers import get_current_run_tree, traceable
from loguru import logger
from mutagen.mp3 import MP3
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import global_config_loaded_from_config_yaml
from app.core.model_selection import select_chat_tts_model
from app.core.voice.tts_catalog import (
    TTS_MODELS,
    is_model_belongs_to_provider,
)
from app.services.global_services import subscription_service
from app.core.voice.tts_api import (
    TTS_PROVIDER_ELEVENLABS,
    TTS_PROVIDER_GEMINI,
    VOICE_ID_PREFIX_ELEVENLABS,
    VOICE_ID_PREFIX_GEMINI,
    VOICE_MESSAGE_NARRATION_MODE_SETTINGS_KEY,
    ElevenLabsTTSAPI,
    GeminiTTSAPI,
    TTSRequest,
    TTSResult,
    VoiceMessageNarrationMode,
    get_gemini_voices,
    is_gemini_voice,
    parse_voice_id,
    resolve_voice_message_narration_mode,
    select_default_gemini_voice_for_imate_gender,
)
from app.external_services.gcs import build_storage_url_pair
from app.external_services.fakes.tts import FakeTextToSpeechAPI
from app.services.gcs_service import GCSService

# 性别到音色ID的映射
GENDER_VOICE_MAPPING = {
    "MALE": "rHWSYoq8UlV0YIBKMryp",
    "FEMALE": "4tRn1lSkEn13EVTuqb0g",
    "OTHER": "O7p2vmz2iEYgMXxkbsif",
}

TTS_MODEL_SOURCE_EXPLICIT = "explicit"
TTS_MODEL_SOURCE_CONFIG = "config"
TTS_MODEL_SOURCE_SUBSCRIPTION = "subscription"


def get_voice_message_narration_mode_from_agent_settings(
    agent_settings: Any,
) -> VoiceMessageNarrationMode:
    if isinstance(agent_settings, dict):
        raw_mode = agent_settings.get(VOICE_MESSAGE_NARRATION_MODE_SETTINGS_KEY)
        if raw_mode is not None:
            return resolve_voice_message_narration_mode(raw_mode)
    return resolve_voice_message_narration_mode(
        global_config_loaded_from_config_yaml.tts.voice_message_narration_mode
    )


@dataclass(frozen=True)
class VoiceGenerationResult:
    """
    Structured voice generation result:
    - gcs_url: canonical gs:// URL
    - gcs_http_url: canonical https://storage.googleapis.com URL
    - duration_seconds: audio duration in seconds
    """

    gcs_url: str
    gcs_http_url: str
    duration_seconds: float

    def __iter__(self) -> Iterator[Any]:
        """
        Backward compatibility for existing callers:
        `audio_url, audio_duration = voice_result`
        """
        yield self.gcs_http_url
        yield self.duration_seconds


def build_voice_gcs_urls(storage_url: str) -> Tuple[str, str]:
    return build_storage_url_pair(storage_url)


def _process_outputs_generate_voice(
    output: Optional[VoiceGenerationResult],
) -> Dict[str, Any]:
    if output is None:
        return {"status": "no_result"}
    return {
        "status": "success",
        "gcs_url": output.gcs_url,
        "gcs_http_url": output.gcs_http_url,
        "duration_seconds": output.duration_seconds,
    }


def _process_outputs_tts_fallback(
    output: Optional[Tuple[bytes, str]],
) -> Dict[str, Any]:
    if output is None:
        return {"status": "no_result"}
    audio_bytes, mime_type = output
    return {
        "status": "success",
        "audio_bytes_len": len(audio_bytes),
        "mime_type": mime_type,
    }


def _process_outputs_call_tts_api(
    output: Optional[Tuple[bytes, float, str, str]],
) -> Dict[str, Any]:
    if output is None:
        return {"status": "no_result"}
    audio_bytes, duration_seconds, mime_type, provider_used = output
    return {
        "status": "success",
        "audio_bytes_len": len(audio_bytes),
        "duration_seconds": duration_seconds,
        "mime_type": mime_type,
        "provider_used": provider_used,
    }


class VoiceService:
    """语音生成服务"""

    def __init__(self):
        self.config = global_config_loaded_from_config_yaml.elevenlabs
        self.gcs_service = GCSService()
        if global_config_loaded_from_config_yaml.tts.use_fake_tts:
            self.tts_api = FakeTextToSpeechAPI()
            self.gemini_tts_api = FakeTextToSpeechAPI()
        else:
            # 语音元数据（音色列表/详情）来自 ElevenLabs 和 Gemini 预置音色；
            # 语音生成根据 voice_id 自动选择对应的 TTS 服务（Gemini 或 ElevenLabs）。
            self.tts_api = ElevenLabsTTSAPI(api_key=self.config.api_key)
            self.gemini_tts_api = GeminiTTSAPI()

    def _validate_model_provider_match(
        self, *, provider_selected: str, model_selected: str
    ) -> None:
        if not is_model_belongs_to_provider(model_selected, provider_selected):
            allowed_for_provider = [
                model.id_on_provider
                for model in TTS_MODELS
                if model.provider == provider_selected
            ]
            raise ValueError(
                f"TTS model/provider mismatch: provider={provider_selected}, "
                f"model={model_selected}, allowed_models={allowed_for_provider}"
            )

    def _clean_text_for_voice(self, text: str) -> str:
        """
        清理文本内容，移除不需要语音化的部分

        移除规则：
        1. *号包裹的心理描写，如 *心想：这是什么情况*
        2. 中文括号包裹的动作描写，如 （轻声说道）、（微笑着）
        3. 英文括号包裹的动作描写，如 (slowly) 、(whispers)

        Args:
            text: 原始文本

        Returns:
            清理后的文本
        """
        if not text:
            return text

        cleaned_text = text

        # 移除中文括号包裹的内容（动作描写）
        # 匹配 （...） 格式的内容
        cleaned_text = re.sub(r"（[^）]*）", "", cleaned_text)

        # 移除英文括号包裹的内容（动作描写）
        # 匹配 (...) 格式的内容
        cleaned_text = re.sub(r"\([^)]*\)", "", cleaned_text)

        # 清理多余的空白字符
        cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()

        return cleaned_text

    @staticmethod
    def _set_trace_metadata(**metadata: Any) -> None:
        run = get_current_run_tree()
        if run is None:
            return
        if run.metadata is None:
            run.metadata = {}
        for key, value in metadata.items():
            if value is not None:
                run.metadata[key] = value

    def _trace_and_return_none(self, reason: str, **metadata: Any) -> None:
        self._set_trace_metadata(
            status="no_result",
            failure_reason=reason,
            **metadata,
        )
        return None

    async def resolve_tts_model(
        self,
        *,
        provider_selected: str,
        db: Optional[AsyncSession],
        user: Optional[Any],
    ) -> Tuple[str, str]:
        """按 provider / 订阅 / 配置解析 TTS model id（与 tts_catalog 查表无关）。"""
        if provider_selected == TTS_PROVIDER_GEMINI:
            if user and db:
                subscription = await subscription_service.get_user_current_subscription(
                    db, user.id
                )
                model_selected = select_chat_tts_model(
                    user=user, is_subscribed=bool(subscription)
                )
                return model_selected, TTS_MODEL_SOURCE_SUBSCRIPTION

            return (
                global_config_loaded_from_config_yaml.agent.free_user_chat_tts_model,
                TTS_MODEL_SOURCE_CONFIG,
            )

        return self.config.model, TTS_MODEL_SOURCE_CONFIG

    def prepare_synthesis_voice_id_and_text(
        self,
        text: str,
        voice_id: Optional[str],
        agent_gender: Optional[str],
    ) -> Tuple[Optional[str], str]:
        """解析 voice_id 并按 TTS 链路规则清理文本（与 generate_voice 内一致）。"""
        _voice_id_for_decision = voice_id
        if not _voice_id_for_decision:
            _voice_id_for_decision = (
                GENDER_VOICE_MAPPING.get(agent_gender)
                if agent_gender
                else self.config.voice_id
            )
        use_prompted_gemini = (
            is_gemini_voice(_voice_id_for_decision)
            and global_config_loaded_from_config_yaml.tts.use_gemini_prompted_tts
        )
        use_gemini_then_elevenlabs_voice_changer = (
            (not is_gemini_voice(_voice_id_for_decision))
            and global_config_loaded_from_config_yaml.tts.enable_gemini_tts_then_elevenlabs_voice_changer_for_imate
        )
        if not (use_prompted_gemini or use_gemini_then_elevenlabs_voice_changer):
            text = self._clean_text_for_voice(text)
        if len(text) > self.config.max_text_length:
            text = text[: self.config.max_text_length]
        return _voice_id_for_decision, text

    async def record_voice_usage(
        self,
        *,
        db: AsyncSession,
        user: Any,
        text_length: int,
        voice_id: str,
        cached: bool,
    ) -> None:
        try:
            await subscription_service.record_usage(
                db,
                user.id,
                "voice_generation",
                1,
                extra_data={
                    "text_length": text_length,
                    "voice_id": voice_id,
                    "cached": cached,
                },
            )
        except Exception as e:
            logger.warning(f"记录语音生成用量失败: {str(e)}")

    @traceable(
        name="generate_voice_no_quota_limit_check",
        run_type="chain",
        process_outputs=_process_outputs_generate_voice,
    )
    async def generate_voice_no_quota_limit_check(
        self,
        text: str,
        voice_id: Optional[str],
        language: str,
        model: str,
        model_source: str,
        agent_gender: Optional[str],
        voice_message_narration_mode: Optional[Any],
        gemini_source_model: Optional[str],
    ) -> Optional[VoiceGenerationResult]:
        """
        仅 TTS + GCS + 异步写缓存；不含配额检查、DB 缓存读、用量记录。
        调用方须先配额检查 / voice_cache_service.get_cached_voice / record_voice_usage。
        """
        narration_mode = resolve_voice_message_narration_mode(
            voice_message_narration_mode
        )

        if not self.config.enabled:
            logger.warning("ElevenLabs语音生成已禁用")
            return self._trace_and_return_none("tts_disabled")

        if not text.strip():
            logger.warning("文本内容为空，跳过语音生成")
            return self._trace_and_return_none("empty_input_text")

        _voice_id_for_decision = voice_id
        if not _voice_id_for_decision:
            _voice_id_for_decision = (
                GENDER_VOICE_MAPPING.get(agent_gender)
                if agent_gender
                else self.config.voice_id
            )
        use_prompted_gemini = (
            is_gemini_voice(_voice_id_for_decision)
            and global_config_loaded_from_config_yaml.tts.use_gemini_prompted_tts
        )
        use_gemini_then_elevenlabs_voice_changer = (
            (not is_gemini_voice(_voice_id_for_decision))
            and global_config_loaded_from_config_yaml.tts.enable_gemini_tts_then_elevenlabs_voice_changer_for_imate
        )
        voice_id = _voice_id_for_decision

        original_text = text
        if not (
            use_prompted_gemini or use_gemini_then_elevenlabs_voice_changer
        ):
            logger.debug(f"清理文本: {text}")
            text = self._clean_text_for_voice(text)

        if not text.strip():
            logger.warning(
                "文本清理后为空（可能全部是心理/动作描写），跳过语音生成"
            )
            return self._trace_and_return_none("empty_text_after_cleaning")

        if text != original_text:
            logger.debug(
                f"文本已清理，原长度: {len(original_text)}, 清理后长度: {len(text)}"
            )

        if len(text) > self.config.max_text_length:
            logger.warning(
                f"文本长度超过限制 {self.config.max_text_length}，截断处理"
            )
            text = text[: self.config.max_text_length]

        try:
            if not voice_id:
                logger.warning(
                    f"无法确定音色ID: agent_gender={agent_gender}, 配置文件voice_id={self.config.voice_id}"
                )
                return self._trace_and_return_none("missing_voice_id")

            provider_selected = (
                TTS_PROVIDER_GEMINI
                if is_gemini_voice(voice_id)
                else TTS_PROVIDER_ELEVENLABS
            )
            self._validate_model_provider_match(
                provider_selected=provider_selected,
                model_selected=model,
            )
            if gemini_source_model is not None:
                self._validate_model_provider_match(
                    provider_selected=TTS_PROVIDER_GEMINI,
                    model_selected=gemini_source_model,
                )

            logger.debug(
                f"开始语音生成(无配额检查): voice_id={voice_id}, provider_selected={provider_selected}, "
                f"model_selected={model}, model_source={model_source}, language={language}, "
                f"text_length={len(text)}"
            )

            audio_result = await self._call_tts_api(
                text=text,
                voice_id=voice_id,
                model=model,
                language=language,
                voice_message_narration_mode=narration_mode,
                agent_gender=agent_gender,
                gemini_source_model=gemini_source_model,
            )
            if not audio_result:
                logger.error(
                    "TTS 生成返回空数据: provider_selected={}, model_selected={}, "
                    "model_source={}, final_status={}",
                    provider_selected,
                    model,
                    model_source,
                    "failed",
                )
                return self._trace_and_return_none(
                    "tts_provider_returned_empty",
                    provider_selected=provider_selected,
                    model_selected=model,
                    model_source=model_source,
                )

            audio_data, duration, mime_type, provider_used = audio_result
            final_model_selected = model
            if (
                provider_selected == TTS_PROVIDER_GEMINI
                and provider_used == TTS_PROVIDER_ELEVENLABS
            ):
                final_model_selected = self.config.model

            file_name = self._generate_file_name(
                text, voice_id, model, self._get_audio_extension(mime_type)
            )
            upload_task = asyncio.create_task(
                self.gcs_service.upload_voice_file(
                    file_name,
                    audio_data,
                    content_type=mime_type or "application/octet-stream",
                )
            )
            audio_url = await upload_task

            if not audio_url:
                logger.error("GCS上传失败")
                return self._trace_and_return_none(
                    "gcs_upload_failed",
                    provider_selected=provider_selected,
                    model_selected=model,
                )

            gcs_url, gcs_http_url = build_voice_gcs_urls(audio_url)

            from app.services.voice_cache_service import voice_cache_service

            asyncio.create_task(
                voice_cache_service.save_voice_cache(
                    None,
                    text,
                    voice_id,
                    model,
                    language,
                    gcs_http_url,
                    duration,
                    len(audio_data),
                )
            )

            self._set_trace_metadata(
                status="success",
                cache_hit=False,
                provider_selected=provider_selected,
                model_selected=final_model_selected,
                model_source=model_source,
                final_provider=provider_used,
            )
            return VoiceGenerationResult(
                gcs_url=gcs_url,
                gcs_http_url=gcs_http_url,
                duration_seconds=duration,
            )

        except ValueError:
            logger.error("语音生成参数校验失败（provider/model 不一致）")
            self._set_trace_metadata(
                status="error",
                failure_reason="provider_model_mismatch",
            )
            raise
        except Exception as e:
            logger.error(f"语音生成失败: {str(e)}")
            logger.exception("语音生成异常详细信息:")
            return self._trace_and_return_none(
                "unexpected_exception",
                exception_type=type(e).__name__,
                exception_message=str(e),
            )

    @traceable(
        name="generate_voice",
        run_type="chain",
        process_outputs=_process_outputs_generate_voice,
    )
    async def generate_voice(
        self,
        text: str,
        voice_id: Optional[str] = None,
        language: str = "zh",
        model: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        agent_gender: Optional[str] = None,
        user: Optional[Any] = None,
        voice_message_narration_mode: Optional[Any] = None,
    ) -> Optional[VoiceGenerationResult]:
        """
        生成语音并上传到GCS

        Args:
            text: 要转换的文本
            voice_id: 语音ID，如果为None则根据agent_gender选择默认音色
            language: 语言代码
            model: 模型名称，默认使用配置中的
            db: 数据库会话，用于缓存查询
            agent_gender: Agent性别，用于选择默认音色（MALE/FEMALE/OTHER）
            user: 用户对象，用于限制检查和用量记录

        Returns:
            语音文件 URL 结果（含 gs:// 与 https:// URL 及音频时长），失败返回 None

        Legacy 入口：委托 resolve_tts_model / voice_cache_service.get_cached_voice /
        generate_voice_no_quota_limit_check / record_voice_usage。带 user+db 的 C 端路径
        优先使用 chat_assistant_voice.produce_voice_for_user。
        """
        if not self.config.enabled:
            logger.warning("ElevenLabs语音生成已禁用")
            return self._trace_and_return_none("tts_disabled")

        if not text.strip():
            logger.warning("文本内容为空，跳过语音生成")
            return self._trace_and_return_none("empty_input_text")

        if user and db:
            (
                is_allowed,
                used_count,
                limit,
            ) = await subscription_service.check_voice_generation_limit(db, user)
            if not is_allowed:
                logger.warning(
                    f"用户 {user.id} 已达到语音生成限制: {used_count}/{limit}"
                )
                return self._trace_and_return_none(
                    "voice_generation_limit_reached",
                    used_count=used_count,
                    limit=limit,
                )

        try:
            synthesis_voice_id, synthesis_text = (
                self.prepare_synthesis_voice_id_and_text(
                    text, voice_id, agent_gender
                )
            )
            if not synthesis_text.strip():
                logger.warning("文本清理后为空（可能全部是心理/动作描写），跳过语音生成")
                return self._trace_and_return_none("empty_text_after_cleaning")
            if not synthesis_voice_id:
                logger.warning(
                    f"无法确定音色ID: agent_gender={agent_gender}, 配置文件voice_id={self.config.voice_id}"
                )
                return self._trace_and_return_none("missing_voice_id")

            provider_selected = (
                TTS_PROVIDER_GEMINI
                if is_gemini_voice(synthesis_voice_id)
                else TTS_PROVIDER_ELEVENLABS
            )
            if model is not None:
                model_selected = model
                model_source = TTS_MODEL_SOURCE_EXPLICIT
            else:
                model_selected, model_source = await self.resolve_tts_model(
                    provider_selected=provider_selected,
                    db=db,
                    user=user,
                )
            self._validate_model_provider_match(
                provider_selected=provider_selected,
                model_selected=model_selected,
            )
            gemini_source_model: Optional[str] = None
            if (
                provider_selected == TTS_PROVIDER_ELEVENLABS
                and global_config_loaded_from_config_yaml.tts.enable_gemini_tts_then_elevenlabs_voice_changer_for_imate
            ):
                gemini_source_model, _ = await self.resolve_tts_model(
                    provider_selected=TTS_PROVIDER_GEMINI,
                    db=db,
                    user=user,
                )
                self._validate_model_provider_match(
                    provider_selected=TTS_PROVIDER_GEMINI,
                    model_selected=gemini_source_model,
                )

            if db:
                from app.services.voice_cache_service import voice_cache_service

                cached = await voice_cache_service.get_cached_voice(
                    db,
                    synthesis_text,
                    synthesis_voice_id,
                    model_selected,
                    language,
                )
                if cached:
                    if user:
                        await self.record_voice_usage(
                            db=db,
                            user=user,
                            text_length=len(synthesis_text),
                            voice_id=synthesis_voice_id,
                            cached=True,
                        )
                    self._set_trace_metadata(
                        status="success",
                        cache_hit=True,
                        provider_selected=provider_selected,
                        model_selected=model_selected,
                        model_source=model_source,
                    )
                    return cached

            result = await self.generate_voice_no_quota_limit_check(
                text=text,
                voice_id=voice_id,
                language=language,
                model=model_selected,
                model_source=model_source,
                agent_gender=agent_gender,
                voice_message_narration_mode=voice_message_narration_mode,
                gemini_source_model=gemini_source_model,
            )
            if result and user and db:
                await self.record_voice_usage(
                    db=db,
                    user=user,
                    text_length=len(synthesis_text),
                    voice_id=synthesis_voice_id,
                    cached=False,
                )
            return result

        except ValueError:
            logger.error("语音生成参数校验失败（provider/model 不一致）")
            self._set_trace_metadata(
                status="error",
                failure_reason="provider_model_mismatch",
            )
            raise
        except Exception as e:
            logger.error(f"语音生成失败: {str(e)}")
            logger.exception("语音生成异常详细信息:")
            return self._trace_and_return_none(
                "unexpected_exception",
                exception_type=type(e).__name__,
                exception_message=str(e),
            )

    def _get_audio_extension(self, mime_type: str) -> str:
        normalized = (mime_type or "").lower()
        if normalized.startswith("audio/wav") or normalized.startswith(
            "audio/x-wav"
        ):
            return ".wav"
        if normalized in {"audio/mpeg", "audio/mp3"}:
            return ".mp3"
        # Gemini TTS 常见返回 PCM 后会被封装成 WAV；未知类型默认用 wav，便于播放与兼容
        return ".wav"

    @traceable(
        name="tts_fallback_elevenlabs",
        run_type="chain",
        process_outputs=_process_outputs_tts_fallback,
    )
    async def _synthesize_elevenlabs_fallback(
        self,
        text: str,
        voice_id: str,
        model_id: str,
        language: str,
    ) -> Optional[Tuple[bytes, str]]:
        """
        回退到 ElevenLabs 时的 TTS 调用，供 LangSmith 单独追踪。
        返回 (audio_bytes, mime_type) 或 None。
        """
        fallback_req = TTSRequest(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
            output_format=self.config.output_format,
            language_code=language,
        )
        result = await self.tts_api.synthesize(fallback_req)
        if result is None:
            self._set_trace_metadata(
                status="no_result",
                failure_reason="elevenlabs_fallback_empty",
            )
            return None
        self._set_trace_metadata(status="success")
        return (result.audio_bytes, result.mime_type)

    @traceable(
        name="call_tts_api",
        run_type="chain",
        process_outputs=_process_outputs_call_tts_api,
    )
    async def _call_tts_api(
        self,
        text: str,
        voice_id: str,
        model: str,
        language: str,
        voice_message_narration_mode: VoiceMessageNarrationMode = VoiceMessageNarrationMode.DIALOGUE_ONLY,
        agent_gender: Optional[str] = None,
        gemini_source_model: Optional[str] = None,
    ) -> Optional[Tuple[bytes, float, str, str]]:
        """
        调用 TTS 生成语音

        根据 voice_id 自动选择对应的 TTS 服务：
        - 如果是 Gemini 预置音色（如 Zephyr、Puck 等），使用 Gemini TTS
        - 否则使用 ElevenLabs TTS

        Returns:
            音频数据的字节流、时长(秒)、mime_type、实际 provider
        """
        try:
            narration_mode = resolve_voice_message_narration_mode(
                voice_message_narration_mode
            )
            use_gemini = is_gemini_voice(voice_id)
            provider_name = (
                TTS_PROVIDER_GEMINI if use_gemini else TTS_PROVIDER_ELEVENLABS
            )
            self._validate_model_provider_match(
                provider_selected=provider_name,
                model_selected=model,
            )

            logger.debug(
                f"TTS 请求数据: voice_id={voice_id}, model={model}, language={language}, "
                f"text_length={len(text)}, provider={provider_name}, "
                f"voice_message_narration_mode={narration_mode}"
            )

            req = TTSRequest(
                text=text,
                voice_id=voice_id,
                model_id=model,
                output_format=self.config.output_format,
                language_code=language,
                voice_message_narration_mode=narration_mode,
            )

            use_voice_changer = (
                (not use_gemini)
                and global_config_loaded_from_config_yaml.tts.enable_gemini_tts_then_elevenlabs_voice_changer_for_imate
            )

            if use_gemini:
                provider_used = TTS_PROVIDER_GEMINI
                use_prompted = (
                    global_config_loaded_from_config_yaml.tts.use_gemini_prompted_tts
                )
                if use_prompted:
                    tts_result = await self.gemini_tts_api.synthesize_with_roleplay_prompt(
                        req
                    )
                else:
                    tts_result = await self.gemini_tts_api.synthesize(req)
                logger.debug(
                    f"Gemini TTS 路径: use_gemini_prompted_tts={use_prompted}"
                )
                if not tts_result:
                    # Gemini TTS 失败（如未配置凭据），回退到 ElevenLabs
                    logger.warning(
                        "Gemini TTS 失败，回退到 ElevenLabs（使用默认音色）"
                    )
                    self._set_trace_metadata(
                        fallback_used=True,
                        fallback_provider=TTS_PROVIDER_ELEVENLABS,
                    )
                    self._validate_model_provider_match(
                        provider_selected=TTS_PROVIDER_ELEVENLABS,
                        model_selected=self.config.model,
                    )
                    # 使用 ElevenLabs 默认音色，因为 Gemini 音色名无法在 ElevenLabs 中使用
                    fallback_result = (
                        await self._synthesize_elevenlabs_fallback(
                            text=text,
                            voice_id=self.config.voice_id,
                            model_id=self.config.model,
                            language=language,
                        )
                    )
                    if fallback_result is None:
                        logger.error("ElevenLabs TTS 回退也失败")
                        self._set_trace_metadata(
                            status="no_result",
                            failure_reason="gemini_and_fallback_elevenlabs_failed",
                        )
                        return None
                    audio_bytes_fb, mime_type_fb = fallback_result
                    tts_result = TTSResult(
                        audio_bytes=audio_bytes_fb, mime_type=mime_type_fb
                    )
                    provider_used = TTS_PROVIDER_ELEVENLABS
            elif use_voice_changer:
                provider_used = TTS_PROVIDER_ELEVENLABS
                source_voice_name = (
                    select_default_gemini_voice_for_imate_gender(agent_gender)
                )
                source_model = (
                    gemini_source_model
                    or global_config_loaded_from_config_yaml.agent.free_user_chat_tts_model
                )
                gemini_source_req = TTSRequest(
                    text=text,
                    voice_id=f"{VOICE_ID_PREFIX_GEMINI}/{source_voice_name}",
                    model_id=source_model,
                    output_format=self.config.output_format,
                    language_code=language,
                )
                source_audio = await self.gemini_tts_api.synthesize_with_full_dialogue_prompt(
                    gemini_source_req
                )
                if source_audio is None:
                    logger.error(
                        "Gemini full-dialogue TTS 返回空数据，无法进行 ElevenLabs 变声"
                    )
                    self._set_trace_metadata(
                        status="no_result",
                        failure_reason="gemini_source_audio_empty_for_voice_changer",
                    )
                    return None

                tts_result = await self.tts_api.convert_with_voice_changer(
                    source_audio_bytes=source_audio.audio_bytes,
                    source_mime_type=source_audio.mime_type,
                    target_voice_id=voice_id,
                    model_id=self.config.voice_change_model,
                    output_format=self.config.output_format,
                )
                if tts_result is None:
                    logger.error("ElevenLabs voice changer 返回空数据")
                    self._set_trace_metadata(
                        status="no_result",
                        failure_reason="elevenlabs_voice_changer_empty_response",
                    )
                    return None
            else:
                provider_used = TTS_PROVIDER_ELEVENLABS
                tts_result = await self.tts_api.synthesize(req)
                if not tts_result:
                    logger.error("ElevenLabs TTS 返回空数据")
                    self._set_trace_metadata(
                        status="no_result",
                        failure_reason="elevenlabs_empty_response",
                    )
                    return None

            audio_data = tts_result.audio_bytes
            mime_type = tts_result.mime_type

            # 计算音频时长
            duration = self._calculate_audio_duration(
                audio_data, mime_type=mime_type
            )

            logger.debug(
                f"TTS 调用成功 (provider={provider_used})，音频大小: {len(audio_data)} bytes, "
                f"时长: {duration:.2f}秒, mime_type={mime_type}"
            )
            self._set_trace_metadata(
                status="success",
                provider_selected=provider_name,
                provider_used=provider_used,
                mime_type=mime_type,
                voice_changer_enabled=use_voice_changer,
            )
            return (audio_data, duration, mime_type, provider_used)

        except ValueError:
            logger.error("TTS provider/model 校验失败")
            self._set_trace_metadata(
                status="error",
                failure_reason="provider_model_mismatch",
            )
            raise
        except Exception as e:
            logger.error(f"TTS 调用异常: {str(e)}")
            logger.exception("TTS 调用异常详细信息:")
            self._set_trace_metadata(
                status="error",
                failure_reason="unexpected_exception",
                exception_type=type(e).__name__,
                exception_message=str(e),
            )
            return None

    def _generate_file_name(
        self, text: str, voice_id: str, model: str, extension: str
    ) -> str:
        """
        生成语音文件名
        使用文本内容的哈希值确保相同内容生成相同文件名（用于缓存）
        """
        # 创建内容哈希
        content_hash = hashlib.md5(
            f"{text}_{voice_id}_{model}".encode()
        ).hexdigest()

        # 生成文件名：voice_<hash>.<ext>
        file_name = f"voice_{content_hash}{extension}"

        return file_name

    def _calculate_audio_duration(
        self, audio_data: bytes, *, mime_type: str
    ) -> float:
        """
        计算音频数据的时长

        Args:
            audio_data: 音频字节数据

        Returns:
            音频时长（秒）
        """
        normalized = (mime_type or "").lower()
        if normalized.startswith("audio/wav") or normalized.startswith(
            "audio/x-wav"
        ):
            return self._calculate_wav_duration(audio_data)
        if normalized in {"audio/mpeg", "audio/mp3"}:
            return self._calculate_mp3_duration(audio_data)

        # 兜底：先按 mp3 解析，失败再按 wav 解析
        duration = self._calculate_mp3_duration(audio_data)
        if duration > 0:
            return duration
        return self._calculate_wav_duration(audio_data)

    def _calculate_mp3_duration(self, audio_data: bytes) -> float:
        try:
            audio_file = io.BytesIO(audio_data)
            audio = MP3(audio_file)
            return float(audio.info.length or 0.0)
        except Exception as e:
            logger.debug(f"按 MP3 解析时长失败: {str(e)}")
            return 0.0

    def _calculate_wav_duration(self, audio_data: bytes) -> float:
        try:
            with wave.open(io.BytesIO(audio_data), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate <= 0:
                    return 0.0
                return float(frames) / float(rate)
        except Exception as e:
            logger.debug(f"按 WAV 解析时长失败: {str(e)}")
            return 0.0

    def _get_filtered_gemini_voices(
        self,
        search: Optional[str] = None,
        voice_type: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取 Gemini TTS 预置音色列表（带过滤）

        Args:
            search: 搜索音色名称或voice_id
            voice_type: 音色类型过滤（Gemini 音色的 voice_type 都是 "preset"）
            category: 音色分类过滤（Gemini 音色的 category 都是 "prebuilt"）

        Returns:
            过滤后的 Gemini 音色列表
        """
        gemini_voices = get_gemini_voices()
        filtered = []

        for voice in gemini_voices:
            # 检查 voice_type 筛选（Gemini 音色都是 preset 类型）
            if voice_type and voice_type != "preset":
                continue

            # 检查 category 筛选
            if category and voice.get("category") != category:
                continue

            # 应用搜索筛选
            if search:
                voice_name = voice.get("name", "").lower()
                voice_id = voice.get("voice_id", "").lower()
                search_term = search.lower()
                if (
                    search_term not in voice_name
                    and search_term not in voice_id
                ):
                    continue

            filtered.append(voice)

        return filtered

    async def get_available_voices(
        self,
        search: Optional[str] = None,
        page_size: Optional[int] = None,
        voice_type: Optional[str] = None,
        category: Optional[str] = None,
        include_shared: bool = True,
        provider: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取可用的语音列表，支持搜索和过滤

        Args:
            search: 搜索音色名称或voice_id
            page_size: 每页结果数
            voice_type: 音色类型过滤
            category: 音色分类过滤
            include_shared: 是否包含共享音色（Explore页面的音色）
            provider: TTS 服务提供商过滤（"gemini" 或 "elevenlabs"，None 表示返回所有）

        Returns:
            语音列表（合并了 Gemini 预置音色、ElevenLabs 个人音色、预置音色和共享音色）
        """
        all_voices = []
        # 如果没有指定page_size，获取所有音色；否则使用指定的page_size
        actual_page_size = (
            page_size if page_size is not None else 1000
        )  # 使用足够大的数字获取所有音色

        gemini_count = 0
        regular_count = 0
        shared_count = 0

        try:
            # 1. 获取 Gemini TTS 预置音色（放在最前面）
            if provider is None or provider == TTS_PROVIDER_GEMINI:
                gemini_voices = self._get_filtered_gemini_voices(
                    search, voice_type, category
                )
                all_voices.extend(gemini_voices)
                gemini_count = len(gemini_voices)

            # 2. 获取 ElevenLabs 用户音色和预置音色
            if provider is None or provider == TTS_PROVIDER_ELEVENLABS:
                regular_voices = await self._search_regular_voices(
                    search, actual_page_size, voice_type, category
                )
                all_voices.extend(regular_voices)
                regular_count = len(regular_voices)

                # 3. 获取 ElevenLabs 共享音色（Explore页面）
                if include_shared:
                    shared_voices = await self._search_shared_voices(
                        search,
                        actual_page_size,
                        voice_type=voice_type,
                        category=category,
                    )
                    all_voices.extend(shared_voices)
                    shared_count = len(shared_voices)

            # 4. 去重（基于voice_id）
            seen_voice_ids = set()
            unique_voices = []
            for voice in all_voices:
                voice_id = voice.get("voice_id")
                if voice_id and voice_id not in seen_voice_ids:
                    seen_voice_ids.add(voice_id)
                    unique_voices.append(voice)

            # 5. 限制返回数量（只有明确指定page_size时才限制）
            if page_size is not None and page_size > 0:
                unique_voices = unique_voices[:page_size]

            logger.info(
                f"最终返回音色总数: {len(unique_voices)} "
                f"(Gemini: {gemini_count}, 常规: {regular_count}, 共享: {shared_count}, "
                f"page_size限制: {page_size}, include_shared: {include_shared}, provider: {provider})"
            )
            return unique_voices

        except Exception as e:
            logger.error(f"获取语音列表异常: {str(e)}")
            logger.exception("获取语音列表异常详细信息:")
            return []

    async def _search_regular_voices(
        self,
        search: Optional[str] = None,
        page_size: int = 10,
        voice_type: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        搜索常规音色（用户音色 + 预置音色 + professional音色）
        """
        try:
            logger.info(
                f"开始获取所有常规音色 (参数: search={search}, page_size={page_size}, voice_type={voice_type}, category={category})"
            )

            # 1. 获取所有基础语音，包括legacy音色
            voices_response = await self.tts_api.get_all_voices(
                show_legacy=True
            )
            logger.info(f"get_all API返回 {len(voices_response.voices)} 个音色")

            # 转换为字典格式并添加来源标识
            voices_list = []
            personal_count = 0
            preset_count = 0
            professional_count = 0

            for voice in voices_response.voices:
                voice_dict = voice.model_dump()

                # 添加 provider 字段，标识音色来源；voice_id 带 11labs/ 前缀
                voice_dict["provider"] = TTS_PROVIDER_ELEVENLABS
                raw_id = voice_dict.get("voice_id", "")
                voice_dict["voice_id"] = (
                    f"{VOICE_ID_PREFIX_ELEVENLABS}/{raw_id}"
                )

                # 根据category和is_owner确定source和voice_type
                voice_category = voice_dict.get("category", "unknown")
                is_owner = voice_dict.get("is_owner", False)

                if voice_category == "professional":
                    voice_dict["source"] = (
                        "professional"  # 标记为professional音色
                    )
                    professional_count += 1
                else:
                    voice_dict["source"] = "regular"  # 标记为常规音色

                # 根据is_owner字段区分个人音色和预置音色
                if is_owner:
                    voice_dict["voice_type"] = "personal"  # 个人音色
                    personal_count += 1
                else:
                    voice_dict["voice_type"] = "preset"  # 预置音色
                    preset_count += 1

                # 应用筛选逻辑
                # 检查voice_type筛选
                if voice_type and voice_dict["voice_type"] != voice_type:
                    continue

                # 检查category筛选
                if category and voice_category != category:
                    continue

                # 应用搜索筛选
                if search:
                    voice_name = voice_dict.get("name", "").lower()
                    voice_id = voice_dict.get("voice_id", "").lower()
                    search_term = search.lower()
                    if (
                        search_term not in voice_name
                        and search_term not in voice_id
                    ):
                        continue

                voices_list.append(voice_dict)

            logger.info(
                f"处理完成: 总计 {len(voices_list)} 个音色 (个人: {personal_count}, 预置: {preset_count}, professional: {professional_count})"
            )
            return voices_list

        except Exception as e:
            logger.error(f"搜索常规音色异常: {str(e)}")
            logger.exception("搜索常规音色异常详细信息:")
            return []

    async def _search_shared_voices(
        self, search: Optional[str] = None, page_size: int = 30, **kwargs
    ) -> List[Dict[str, Any]]:
        """
        搜索共享音色（Explore页面的音色）

        Args:
            search: 搜索关键词（支持音色名称和voice_id）
            page_size: 每页结果数，最大100
            **kwargs: 其他搜索参数

        Returns:
            共享音色列表
        """
        try:
            # 准备搜索参数
            search_params = {
                "search": search,
                "page_size": min(page_size, 100),  # API限制最大100
                "sort": "created_date",  # 按创建时间排序
            }

            # 添加其他搜索参数
            if "voice_type" in kwargs:
                search_params["category"] = kwargs["voice_type"]
            if "category" in kwargs:
                search_params["category"] = kwargs["category"]

            # 移除None值
            search_params = {
                k: v for k, v in search_params.items() if v is not None
            }

            logger.debug(f"搜索共享音色，参数: {search_params}")

            # 调用 ElevenLabs get_shared API
            voices_response = await self.tts_api.get_shared_voices(
                **search_params
            )

            # 转换为字典格式并添加来源标识
            voices_list = []
            for voice in voices_response.voices:
                voice_dict = voice.model_dump()
                voice_dict["source"] = "shared"  # 标记为共享音色
                voice_dict["provider"] = (
                    TTS_PROVIDER_ELEVENLABS  # 添加 provider 字段
                )
                raw_id = voice_dict.get("voice_id", "")
                voice_dict["voice_id"] = (
                    f"{VOICE_ID_PREFIX_ELEVENLABS}/{raw_id}"
                )
                voices_list.append(voice_dict)

            logger.debug(f"获取到 {len(voices_list)} 个共享音色")
            return voices_list

        except Exception as e:
            logger.error(f"搜索共享音色异常: {str(e)}")
            logger.exception("搜索共享音色异常详细信息:")
            return []

    async def get_voice_info(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """
        获取特定语音的信息
        支持从 Gemini 预置音色、ElevenLabs 常规音色和共享音色中查找。
        支持带前缀（google/xxx、11labs/xxx）与无前缀（兼容旧数据）的 voice_id。
        """
        prefix, raw = parse_voice_id(voice_id)

        # 0. Gemini 预置音色（带 google/ 前缀或无前缀且 is_gemini_voice）
        if prefix == VOICE_ID_PREFIX_GEMINI or (
            prefix == "" and is_gemini_voice(voice_id)
        ):
            gemini_voices = get_gemini_voices()
            lookup_id = (
                voice_id
                if prefix == VOICE_ID_PREFIX_GEMINI
                else f"{VOICE_ID_PREFIX_GEMINI}/{raw}"
            )
            for voice in gemini_voices:
                if voice["voice_id"] == lookup_id:
                    logger.debug(
                        f"从 Gemini 预置音色中找到 voice_id: {voice_id}"
                    )
                    return voice
            logger.debug(
                f"voice_id {voice_id} 匹配 Gemini 格式但未在预置列表中找到"
            )

        try:
            # 1. ElevenLabs 常规音色（用 raw 调 API，返回时统一为 11labs/ 前缀）
            voice = await self.tts_api.get_voice(raw)
            voice_dict = voice.model_dump()
            voice_dict["voice_id"] = f"{VOICE_ID_PREFIX_ELEVENLABS}/{raw}"
            voice_dict["source"] = "regular"
            voice_dict["provider"] = TTS_PROVIDER_ELEVENLABS
            logger.debug(f"从常规音色中找到 voice_id: {voice_id}")
            return voice_dict
        except Exception as e:
            logger.debug(f"从常规音色中获取 {voice_id} 失败: {str(e)}")

        try:
            # 2. 共享音色：用 raw 搜索，匹配带前缀的 voice_id
            logger.debug(f"尝试从共享音色中搜索 voice_id: {voice_id}")
            shared_voices = await self._search_shared_voices(
                search=raw, page_size=50
            )
            prefixed_id = f"{VOICE_ID_PREFIX_ELEVENLABS}/{raw}"
            for voice in shared_voices:
                if (
                    voice.get("voice_id") == prefixed_id
                    or voice.get("voice_id") == voice_id
                ):
                    logger.debug(f"从共享音色中找到 voice_id: {voice_id}")
                    return voice
            logger.debug(f"在共享音色中也未找到 voice_id: {voice_id}")
        except Exception as e:
            logger.error(f"从共享音色中搜索 {voice_id} 异常: {str(e)}")

        logger.warning(f"无法找到音色信息，voice_id: {voice_id}")
        return None


# 创建全局实例
voice_service = VoiceService()
