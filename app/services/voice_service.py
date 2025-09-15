"""
语音生成服务
集成ElevenLabs API进行文本转语音
"""

import asyncio
import base64
import hashlib
import io
import re
from typing import Any, Dict, List, Optional, Tuple

from mutagen.mp3 import MP3

from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import global_config_loaded_from_config_yaml
from app.services.gcs_service import GCSService


class VoiceService:
    """语音生成服务"""

    def __init__(self):
        self.config = global_config_loaded_from_config_yaml.elevenlabs
        self.gcs_service = GCSService()
        self.client = ElevenLabs(api_key=self.config.api_key)

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
    ) -> Optional[Tuple[str, float]]:
        """
        生成语音并上传到GCS

        Args:
            text: 要转换的文本
            voice_id: 语音ID，默认使用配置中的
            language: 语言代码
            model: 模型名称，默认使用配置中的
            db: 数据库会话，用于缓存查询

        Returns:
            语音文件的GCS URL和音频时长(秒)的元组，失败返回None
        """
        if not self.config.enabled:
            logger.warning("ElevenLabs语音生成已禁用")
            return None

        if not text.strip():
            logger.warning("文本内容为空，跳过语音生成")
            return None

        # 清理文本内容，移除心理和动作描写
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

        try:
            # 使用默认配置
            voice_id = voice_id or self.config.voice_id
            model = model or self.config.model

            logger.debug(
                f"开始语音生成: voice_id={voice_id}, model={model}, language={language}, text_length={len(text)}"
            )

            # 并行检查缓存和预准备其他资源
            cached_url = None
            if db:
                logger.debug("检查语音缓存")
                from app.services.voice_cache_service import voice_cache_service

                cached_url = await voice_cache_service.get_cached_voice(
                    db, text, voice_id, model, language
                )
                if cached_url:
                    logger.debug(f"使用缓存的语音文件: {cached_url}")
                    # 访问统计已经在get_cached_voice中异步更新了，这里不需要重复更新
                    return cached_url
                logger.debug("未找到缓存，开始新的语音生成")

            # 生成语音文件
            logger.debug("调用ElevenLabs API")
            audio_result = await self._call_elevenlabs_api(
                text, voice_id, model, language
            )
            if not audio_result:
                logger.error("ElevenLabs API返回空数据")
                return None
            
            audio_data, duration = audio_result

            logger.debug(
                f"ElevenLabs API调用成功，音频数据大小: {len(audio_data)} bytes"
            )

            # 生成唯一文件名
            file_name = self._generate_file_name(text, voice_id, model)
            logger.debug(f"生成文件名: {file_name}")

            # 并行上传到GCS和准备缓存保存
            logger.debug("开始上传到GCS")

            # 创建上传任务
            upload_task = asyncio.create_task(
                self.gcs_service.upload_voice_file(
                    file_name, audio_data, content_type="audio/mpeg"
                )
            )

            # 等待上传完成
            audio_url = await upload_task

            if not audio_url:
                logger.error("GCS上传失败")
                return None

            logger.debug(f"GCS上传成功: {audio_url}")

            # 异步保存到缓存，不阻塞返回
            if audio_url:
                logger.debug("异步保存到语音缓存")
                from app.services.voice_cache_service import voice_cache_service

                asyncio.create_task(
                    voice_cache_service.save_voice_cache(
                        None,
                        text,
                        voice_id,
                        model,
                        language,
                        audio_url,
                        len(audio_data),
                    )
                )
                logger.debug("语音缓存保存任务已启动")

            logger.debug(f"语音生成成功: {file_name}, 时长: {duration:.2f}秒")
            return (audio_url, duration)

        except Exception as e:
            logger.error(f"语音生成失败: {str(e)}")
            logger.exception("语音生成异常详细信息:")
            return None

    async def _call_elevenlabs_api(
        self, text: str, voice_id: str, model: str, language: str
    ) -> Optional[Tuple[bytes, float]]:
        """
        调用ElevenLabs API生成语音

        Returns:
            音频数据的字节流和时长(秒)的元组
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
            response = self.client.text_to_speech.convert_with_timestamps(**kwargs)
            
            # 从base64解码音频数据
            audio_data = base64.b64decode(response.audio_base_64)
            
            # 计算音频时长
            duration = self._calculate_audio_duration(audio_data)
            
            logger.debug(f"ElevenLabs API调用成功，音频大小: {len(audio_data)} bytes, 时长: {duration:.2f}秒")
            return (audio_data, duration)

        except Exception as e:
            logger.error(f"ElevenLabs API调用异常: {str(e)}")
            logger.exception("ElevenLabs API调用异常详细信息:")
            return None

    def _generate_file_name(self, text: str, voice_id: str, model: str) -> str:
        """
        生成语音文件名
        使用文本内容的哈希值确保相同内容生成相同文件名（用于缓存）
        """
        # 创建内容哈希
        content_hash = hashlib.md5(f"{text}_{voice_id}_{model}".encode()).hexdigest()

        # 生成文件名：voice_时间戳_哈希值.mp3
        file_name = f"voice_{content_hash}.mp3"

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
        page_size: Optional[int] = 10,
        voice_type: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取可用的语音列表，支持搜索和过滤

        Args:
            search: 搜索音色名称
            page_size: 每页结果数
            voice_type: 音色类型过滤
            category: 音色分类过滤

        Returns:
            语音列表
        """
        try:
            # 使用 ElevenLabs SDK 的搜索功能
            kwargs = {}
            if page_size is not None:
                kwargs["page_size"] = page_size
            if search is not None:
                kwargs["search"] = search
            if voice_type is not None:
                kwargs["voice_type"] = voice_type
            if category is not None:
                kwargs["category"] = category

            logger.debug(f"获取语音列表，参数: {kwargs}")

            # 调用 ElevenLabs voices search API
            if kwargs:
                # 使用搜索功能
                voices_response = self.client.voices.search(**kwargs)
            else:
                # 获取所有语音
                voices_response = self.client.voices.get_all()

            # 转换为字典格式以保持兼容性
            voices_list = [voice.model_dump() for voice in voices_response.voices]

            logger.debug(f"获取到 {len(voices_list)} 个语音")
            return voices_list

        except Exception as e:
            logger.error(f"获取语音列表异常: {str(e)}")
            logger.exception("获取语音列表异常详细信息:")
            return []

    async def get_voice_info(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """
        获取特定语音的信息

        Args:
            voice_id: 语音ID

        Returns:
            语音信息
        """
        try:
            voice = self.client.voices.get(voice_id)
            return voice.model_dump()
        except Exception as e:
            logger.error(f"获取语音信息异常: {str(e)}")
            return None


# 创建全局实例
voice_service = VoiceService()
