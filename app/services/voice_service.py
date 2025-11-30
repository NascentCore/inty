"""
语音生成服务
集成ElevenLabs API进行文本转语音
"""

import asyncio
import base64
import hashlib
import io
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from loguru import logger
from mutagen.mp3 import MP3
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import global_config_loaded_from_config_yaml
from app.services.gcs_service import GCSService
from app.services.voices.gemini import GeminiVoiceProvider

# 性别到音色ID的映射
GENDER_VOICE_MAPPING = {
    "MALE": "rHWSYoq8UlV0YIBKMryp",
    "FEMALE": "4tRn1lSkEn13EVTuqb0g",
    "OTHER": "O7p2vmz2iEYgMXxkbsif",
}

GEMINI_GENDER_DEFAULT_MAPPING = {
    "MALE": "Charon",
    "FEMALE": "Kore",
    "OTHER": "Zephyr",
}

GEMINI_TO_ELEVEN_VOICE_ID = {
    "kore": "4tRn1lSkEn13EVTuqb0g",
    "charon": "rHWSYoq8UlV0YIBKMryp",
    "zephyr": "O7p2vmz2iEYgMXxkbsif",
}

ELEVEN_TO_GEMINI_VOICE_ID = {value: key for key, value in GEMINI_TO_ELEVEN_VOICE_ID.items()}


class VoiceProvider(str, Enum):
    GEMINI = "gemini"
    ELEVENLABS = "elevenlabs"


@dataclass
class VoiceSelection:
    requested_voice_id: Optional[str]
    gemini_voice_name: Optional[str]
    elevenlabs_voice_id: Optional[str]

    def provider_voice_id(self, provider: VoiceProvider) -> Optional[str]:
        if provider == VoiceProvider.GEMINI:
            voice_name = (self.gemini_voice_name or "").strip()
            if not voice_name:
                return None
            return f"gemini:{voice_name.lower()}"
        return self.elevenlabs_voice_id


class VoiceService:
    """语音生成服务"""

    def __init__(self):
        self.config = global_config_loaded_from_config_yaml.elevenlabs
        self.gemini_config = global_config_loaded_from_config_yaml.gemini_voice
        self.gcs_service = GCSService()
        self._elevenlabs_client: Optional[ElevenLabs] = None
        self.gemini_provider = GeminiVoiceProvider(self.gemini_config)
        if self.config.enabled:
            self._elevenlabs_client = ElevenLabs(api_key=self.config.api_key)

    def _get_elevenlabs_client(self) -> ElevenLabs:
        if self._elevenlabs_client is None:
            self._elevenlabs_client = ElevenLabs(api_key=self.config.api_key)
        return self._elevenlabs_client

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

    async def generate_voice(
        self,
        text: str,
        voice_id: Optional[str] = None,
        language: str = "zh",
        model: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        agent_gender: Optional[str] = None,
        user: Optional[Any] = None,
    ) -> Optional[Tuple[str, float]]:
        """
        生成语音并上传到GCS，优先使用 Gemini 语音模型，失败后回退到 ElevenLabs。
        """
        providers = self._build_provider_sequence()
        if not providers:
            logger.warning("所有语音提供商均已禁用，无法生成语音")
            return None

        if not text or not text.strip():
            logger.warning("文本内容为空，跳过语音生成")
            return None

        if user and db:
            from app.services.global_services import subscription_service

            is_allowed, used_count, limit = await subscription_service.check_voice_generation_limit(
                db, user
            )
            if not is_allowed:
                logger.warning(f"用户 {user.id} 已达到语音生成限制: {used_count}/{limit}")
                return None

        original_text = text
        text = self._clean_text_for_voice(text)

        if not text.strip():
            logger.warning("文本清理后为空（可能全部是心理/动作描写），跳过语音生成")
            return None

        if text != original_text:
            logger.debug(
                f"文本已清理，原长度: {len(original_text)}, 清理后长度: {len(text)}"
            )

        if len(text) > self.config.max_text_length:
            logger.warning(f"文本长度超过限制 {self.config.max_text_length}，截断处理")
            text = text[: self.config.max_text_length]

        selection = self._resolve_voice_selection(voice_id, agent_gender)
        requested_model = model
        text_length = len(text)

        for provider in providers:
            provider_model = self._resolve_provider_model(provider, requested_model)
            provider_voice_id = selection.provider_voice_id(provider)
            if not provider_voice_id:
                logger.debug(f"{provider.value} 无可用音色配置，跳过该提供商")
                continue

            cached_result = await self._get_cached_voice(
                db, text, provider_voice_id, provider_model, language
            )
            if cached_result:
                cached_url, cached_duration = cached_result
                await self._record_voice_usage_if_needed(
                    db,
                    user,
                    text_length,
                    provider_voice_id,
                    provider,
                    cached=True,
                    requested_voice_id=selection.requested_voice_id,
                )
                logger.debug(
                    f"{provider.value} 语音生成使用缓存: {cached_url}, 时长: {cached_duration:.2f}秒"
                )
                return cached_url, cached_duration

            generation_result = await self._invoke_provider_api(
                provider, text, selection, provider_model, language
            )
            if not generation_result:
                logger.warning(f"{provider.value} 语音生成失败，尝试下一个提供商")
                continue

            audio_data, duration, content_type, file_extension = generation_result
            file_name = self._generate_file_name(
                text, provider_voice_id, provider_model, file_extension
            )
            logger.debug(
                f"{provider.value} 语音生成成功，准备上传: voice_id={provider_voice_id}, model={provider_model}"
            )

            audio_url = await self.gcs_service.upload_voice_file(
                file_name, audio_data, content_type=content_type
            )
            if not audio_url:
                logger.error("GCS上传失败，尝试下一个语音提供商")
                continue

            self._schedule_cache_save(
                text,
                provider_voice_id,
                provider_model,
                language,
                audio_url,
                duration,
                len(audio_data),
            )

            await self._record_voice_usage_if_needed(
                db,
                user,
                text_length,
                provider_voice_id,
                provider,
                cached=False,
                requested_voice_id=selection.requested_voice_id,
            )

            logger.debug(f"语音生成成功: {file_name}, 时长: {duration:.2f}秒")
            return audio_url, duration

        logger.error("所有语音提供商均生成失败")
        return None

    def _build_provider_sequence(self) -> List[VoiceProvider]:
        order: List[VoiceProvider] = []
        if self.gemini_config.enabled:
            order.append(VoiceProvider.GEMINI)
        if self.config.enabled:
            order.append(VoiceProvider.ELEVENLABS)
        return order

    def _resolve_provider_model(
        self, provider: VoiceProvider, requested_model: Optional[str]
    ) -> str:
        if requested_model:
            return requested_model
        if provider == VoiceProvider.GEMINI:
            return self.gemini_config.model
        return self.config.model

    def _resolve_voice_selection(
        self, voice_id: Optional[str], agent_gender: Optional[str]
    ) -> VoiceSelection:
        requested_voice_id = voice_id
        resolved_voice_id = voice_id
        gender_key = (agent_gender or "").upper()

        if not resolved_voice_id and gender_key:
            resolved_voice_id = GENDER_VOICE_MAPPING.get(gender_key)
        if not resolved_voice_id:
            resolved_voice_id = self.config.voice_id

        gemini_voice_name: Optional[str] = None
        if requested_voice_id and requested_voice_id.lower().startswith("gemini:"):
            gemini_voice_name = requested_voice_id.split(":", 1)[1].strip() or None
        else:
            gemini_voice_name = self._map_elevenlabs_voice_to_gemini(resolved_voice_id)

        if not gemini_voice_name:
            gemini_voice_name = GEMINI_GENDER_DEFAULT_MAPPING.get(
                gender_key, self.gemini_config.default_voice_name
            )

        fallback_elevenlabs_voice_id = resolved_voice_id
        if requested_voice_id and requested_voice_id.lower().startswith("gemini:"):
            fallback_elevenlabs_voice_id = GEMINI_TO_ELEVEN_VOICE_ID.get(
                (gemini_voice_name or "").lower(), self.config.voice_id
            )
        if not fallback_elevenlabs_voice_id:
            fallback_elevenlabs_voice_id = self.config.voice_id

        return VoiceSelection(
            requested_voice_id=requested_voice_id,
            gemini_voice_name=gemini_voice_name,
            elevenlabs_voice_id=fallback_elevenlabs_voice_id,
        )

    def _map_elevenlabs_voice_to_gemini(
        self, voice_id: Optional[str]
    ) -> Optional[str]:
        if not voice_id:
            return None
        return ELEVEN_TO_GEMINI_VOICE_ID.get(voice_id)

    async def _invoke_provider_api(
        self,
        provider: VoiceProvider,
        text: str,
        selection: VoiceSelection,
        model: str,
        language: str,
    ) -> Optional[Tuple[bytes, float, str, str]]:
        if provider == VoiceProvider.GEMINI:
            voice_name = selection.gemini_voice_name or self.gemini_config.default_voice_name
            if not voice_name:
                logger.warning("Gemini 未配置默认音色，跳过")
                return None
            return await self.gemini_provider.generate_voice(
                text, voice_name, model, language
            )

        if not selection.elevenlabs_voice_id:
            logger.warning("ElevenLabs 未配置可用音色，跳过")
            return None
        return await self._call_elevenlabs_api(
            text, selection.elevenlabs_voice_id, model, language
        )

    async def _get_cached_voice(
        self,
        db: Optional[AsyncSession],
        text: str,
        voice_id: str,
        model: str,
        language: str,
    ) -> Optional[Tuple[str, float]]:
        if not db:
            return None

        from app.services.voice_cache_service import voice_cache_service

        return await voice_cache_service.get_cached_voice(
            db, text, voice_id, model, language
        )

    def _schedule_cache_save(
        self,
        text: str,
        voice_id: str,
        model: str,
        language: str,
        audio_url: str,
        duration: float,
        file_size: int,
    ) -> None:
        from app.services.voice_cache_service import voice_cache_service

        logger.debug("异步保存到语音缓存")
        asyncio.create_task(
            voice_cache_service.save_voice_cache(
                None,
                text,
                voice_id,
                model,
                language,
                audio_url,
                duration,
                file_size,
            )
        )

    async def _record_voice_usage_if_needed(
        self,
        db: Optional[AsyncSession],
        user: Optional[Any],
        text_length: int,
        voice_id: str,
        provider: VoiceProvider,
        cached: bool,
        requested_voice_id: Optional[str],
    ) -> None:
        if not user or not db:
            return

        from app.services.global_services import subscription_service

        extra = {
            "text_length": text_length,
            "voice_id": voice_id,
            "provider": provider.value,
            "cached": cached,
        }
        if requested_voice_id:
            extra["requested_voice_id"] = requested_voice_id

        try:
            await subscription_service.record_usage(
                db, user.id, "voice_generation", 1, extra_data=extra
            )
        except Exception as e:
            logger.warning(f"记录语音生成用量失败: {str(e)}")

    async def _call_elevenlabs_api(
        self, text: str, voice_id: str, model: str, language: str
    ) -> Optional[Tuple[bytes, float, str, str]]:
        """
        调用ElevenLabs API生成语音

        Returns:
            音频数据的字节流、时长(秒)、content-type、文件扩展名
        """
        try:
            logger.debug(
                f"ElevenLabs API请求数据: voice_id={voice_id}, model={model}, text_length={len(text)}"
            )

            # 创建语音设置
            voice_settings = VoiceSettings(stability=0.5, similarity_boost=0.5)

            # 准备参数
            kwargs = {
                "text": text,
                "voice_id": voice_id,
                "model_id": model,
                "output_format": self.config.output_format,
                "voice_settings": voice_settings,
            }

            # 注意：eleven_multilingual_v2 模型不支持 language_code 参数
            # 只有特定模型才支持 language_code 参数
            if "turbo" in model.lower() and "multilingual" in model.lower():
                kwargs["language_code"] = language

            # 调用官方SDK的convert_with_timestamps方法
            client = self._get_elevenlabs_client()
            response = client.text_to_speech.convert_with_timestamps(**kwargs)

            # 从base64解码音频数据
            audio_data = base64.b64decode(response.audio_base_64)

            # 计算音频时长
            duration = self._calculate_audio_duration(audio_data)

            logger.debug(
                f"ElevenLabs API调用成功，音频大小: {len(audio_data)} bytes, 时长: {duration:.2f}秒"
            )
            return (audio_data, duration, "audio/mpeg", ".mp3")

        except Exception as e:
            logger.error(f"ElevenLabs API调用异常: {str(e)}")
            logger.exception("ElevenLabs API调用异常详细信息:")
            return None

    def _generate_file_name(
        self, text: str, voice_id: str, model: str, extension: str = ".mp3"
    ) -> str:
        """
        生成语音文件名
        使用文本内容的哈希值确保相同内容生成相同文件名（用于缓存）
        """
        # 创建内容哈希
        content_hash = hashlib.md5(f"{text}_{voice_id}_{model}".encode()).hexdigest()

        # 生成文件名：voice_哈希值.<ext>
        file_name = f"voice_{content_hash}{extension}"

        return file_name

    def _calculate_audio_duration(self, audio_data: bytes) -> float:
        """
        计算音频数据的时长

        Args:
            audio_data: 音频字节数据

        Returns:
            音频时长（秒）
        """
        try:
            # 使用mutagen计算MP3时长，从字节数据
            audio_file = io.BytesIO(audio_data)
            audio = MP3(audio_file)
            duration_seconds = audio.info.length
            return duration_seconds
        except Exception as e:
            logger.error(f"计算音频时长失败: {str(e)}")
            return 0.0

    async def get_available_voices(
        self,
        search: Optional[str] = None,
        page_size: Optional[int] = None,
        voice_type: Optional[str] = None,
        category: Optional[str] = None,
        include_shared: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        获取可用的语音列表，支持搜索和过滤

        Args:
            search: 搜索音色名称或voice_id
            page_size: 每页结果数
            voice_type: 音色类型过滤
            category: 音色分类过滤
            include_shared: 是否包含共享音色（Explore页面的音色）

        Returns:
            语音列表（合并了个人音色、预置音色和共享音色）
        """
        all_voices = []
        # 如果没有指定page_size，获取所有音色；否则使用指定的page_size
        actual_page_size = (
            page_size if page_size is not None else 1000
        )  # 使用足够大的数字获取所有音色

        try:
            # 1. 获取用户音色和预置音色
            regular_voices = await self._search_regular_voices(
                search, actual_page_size, voice_type, category
            )
            all_voices.extend(regular_voices)

            # 2. 获取共享音色（Explore页面）
            if include_shared:
                shared_voices = await self._search_shared_voices(
                    search, actual_page_size, voice_type=voice_type, category=category
                )
                all_voices.extend(shared_voices)

            # 3. 去重（基于voice_id）
            seen_voice_ids = set()
            unique_voices = []
            for voice in all_voices:
                voice_id = voice.get("voice_id")
                if voice_id and voice_id not in seen_voice_ids:
                    seen_voice_ids.add(voice_id)
                    unique_voices.append(voice)

            # 4. 限制返回数量（只有明确指定page_size时才限制）
            if page_size is not None and page_size > 0:
                unique_voices = unique_voices[:page_size]

            shared_count = (
                len(shared_voices)
                if include_shared and "shared_voices" in locals()
                else 0
            )
            logger.info(
                f"最终返回音色总数: {len(unique_voices)} (常规: {len(regular_voices)}, 共享: {shared_count}, "
                f"page_size限制: {page_size}, include_shared: {include_shared})"
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
            client = self._get_elevenlabs_client()
            voices_response = client.voices.get_all(show_legacy=True)
            logger.info(f"get_all API返回 {len(voices_response.voices)} 个音色")

            # 转换为字典格式并添加来源标识
            voices_list = []
            personal_count = 0
            preset_count = 0
            professional_count = 0

            for voice in voices_response.voices:
                voice_dict = voice.model_dump()

                # 根据category和is_owner确定source和voice_type
                voice_category = voice_dict.get("category", "unknown")
                is_owner = voice_dict.get("is_owner", False)

                if voice_category == "professional":
                    voice_dict["source"] = "professional"  # 标记为professional音色
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
                    if search_term not in voice_name and search_term not in voice_id:
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
            search_params = {k: v for k, v in search_params.items() if v is not None}

            logger.debug(f"搜索共享音色，参数: {search_params}")

            # 调用 ElevenLabs get_shared API
            client = self._get_elevenlabs_client()
            voices_response = client.voices.get_shared(**search_params)

            # 转换为字典格式并添加来源标识
            voices_list = []
            for voice in voices_response.voices:
                voice_dict = voice.model_dump()
                voice_dict["source"] = "shared"  # 标记为共享音色
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
        支持从常规音色和共享音色中查找

        Args:
            voice_id: 语音ID

        Returns:
            语音信息
        """
        try:
            # 1. 先尝试从常规音色中获取（用户音色 + 预置音色）
            client = self._get_elevenlabs_client()
            voice = client.voices.get(voice_id)
            voice_dict = voice.model_dump()
            voice_dict["source"] = "regular"
            logger.debug(f"从常规音色中找到 voice_id: {voice_id}")
            return voice_dict
        except Exception as e:
            logger.debug(f"从常规音色中获取 {voice_id} 失败: {str(e)}")

        try:
            # 2. 如果常规音色中没有，尝试从共享音色中搜索
            logger.debug(f"尝试从共享音色中搜索 voice_id: {voice_id}")
            shared_voices = await self._search_shared_voices(
                search=voice_id, page_size=50
            )

            # 在搜索结果中查找精确匹配的voice_id
            for voice in shared_voices:
                if voice.get("voice_id") == voice_id:
                    logger.debug(f"从共享音色中找到 voice_id: {voice_id}")
                    return voice

            logger.debug(f"在共享音色中也未找到 voice_id: {voice_id}")

        except Exception as e:
            logger.error(f"从共享音色中搜索 {voice_id} 异常: {str(e)}")

        logger.warning(f"无法找到音色信息，voice_id: {voice_id}")
        return None


# 创建全局实例
voice_service = VoiceService()
