"""
语音生成服务
集成ElevenLabs API进行文本转语音
"""
import asyncio
import hashlib
import uuid
from typing import Optional, Dict, Any, List
from io import BytesIO
import aiohttp
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.gcs_service import GCSService


class VoiceService:
    """语音生成服务"""
    
    def __init__(self):
        self.config = settings.elevenlabs
        self.gcs_service = GCSService()
        self.base_url = "https://api.elevenlabs.io/v1"
        
    async def generate_voice(
        self, 
        text: str, 
        voice_id: Optional[str] = None,
        language: str = "zh",
        model: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Optional[str]:
        """
        生成语音并上传到GCS
        
        Args:
            text: 要转换的文本
            voice_id: 语音ID，默认使用配置中的
            language: 语言代码
            model: 模型名称，默认使用配置中的
            db: 数据库会话，用于缓存查询
            
        Returns:
            语音文件的GCS URL，失败返回None
        """
        if not self.config.enabled:
            logger.warning("ElevenLabs语音生成已禁用")
            return None
            
        if not text.strip():
            logger.warning("文本内容为空，跳过语音生成")
            return None
            
        if len(text) > self.config.max_text_length:
            logger.warning(f"文本长度超过限制 {self.config.max_text_length}，截断处理")
            text = text[:self.config.max_text_length]
            
        try:
            # 使用默认配置
            voice_id = voice_id or self.config.voice_id
            model = model or self.config.model
            
            logger.info(f"开始语音生成: voice_id={voice_id}, model={model}, language={language}, text_length={len(text)}")
            
            # 检查缓存
            if db:
                logger.debug("检查语音缓存")
                from app.services.voice_cache_service import voice_cache_service
                cached_url = await voice_cache_service.get_cached_voice(
                    db, text, voice_id, model, language
                )
                if cached_url:
                    logger.info(f"使用缓存的语音文件: {cached_url}")
                    return cached_url
                logger.debug("未找到缓存，开始新的语音生成")
            
            # 生成语音文件
            logger.debug("调用ElevenLabs API")
            audio_data = await self._call_elevenlabs_api(text, voice_id, model, language)
            if not audio_data:
                logger.error("ElevenLabs API返回空数据")
                return None
            
            logger.info(f"ElevenLabs API调用成功，音频数据大小: {len(audio_data)} bytes")
                
            # 生成唯一文件名
            file_name = self._generate_file_name(text, voice_id, model)
            logger.debug(f"生成文件名: {file_name}")
            
            # 上传到GCS
            logger.debug("开始上传到GCS")
            audio_url = await self.gcs_service.upload_voice_file(
                file_name, 
                audio_data, 
                content_type="audio/mpeg"
            )
            
            if not audio_url:
                logger.error("GCS上传失败")
                return None
                
            logger.info(f"GCS上传成功: {audio_url}")
            
            # 保存到缓存
            if db and audio_url:
                logger.debug("保存到语音缓存")
                from app.services.voice_cache_service import voice_cache_service
                await voice_cache_service.save_voice_cache(
                    db, text, voice_id, model, language, audio_url, len(audio_data)
                )
                logger.debug("语音缓存保存成功")
            
            logger.info(f"语音生成成功: {file_name}")
            return audio_url
            
        except Exception as e:
            logger.error(f"语音生成失败: {str(e)}")
            logger.exception("语音生成异常详细信息:")
            return None
    
    async def _call_elevenlabs_api(
        self, 
        text: str, 
        voice_id: str, 
        model: str,
        language: str
    ) -> Optional[bytes]:
        """
        调用ElevenLabs API生成语音
        
        Returns:
            音频数据的字节流
        """
        url = f"{self.base_url}/text-to-speech/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.config.api_key
        }
        
        data = {
            "text": text,
            "model_id": model,
            "output_format": self.config.output_format,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        # 注意：eleven_multilingual_v2 模型不支持 language_code 参数
        # 只有特定模型才支持 language_code 参数
        if "turbo" in model.lower() and "multilingual" in model.lower():
            data["language_code"] = language
        
        try:
            logger.debug(f"ElevenLabs API请求URL: {url}")
            logger.debug(f"ElevenLabs API请求数据: voice_id={voice_id}, model={model}, text_length={len(text)}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers) as response:
                    logger.debug(f"ElevenLabs API响应状态: {response.status}")
                    if response.status == 200:
                        audio_data = await response.read()
                        logger.info(f"ElevenLabs API调用成功，音频大小: {len(audio_data)} bytes")
                        return audio_data
                    else:
                        error_text = await response.text()
                        logger.error(f"ElevenLabs API调用失败: {response.status} - {error_text}")
                        return None
                        
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
    
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        获取可用的语音列表
        
        Returns:
            语音列表
        """
        url = f"{self.base_url}/voices"
        
        headers = {
            "Accept": "application/json",
            "xi-api-key": self.config.api_key
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("voices", [])
                    else:
                        logger.error(f"获取语音列表失败: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"获取语音列表异常: {str(e)}")
            return []
    
    async def get_voice_info(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """
        获取特定语音的信息
        
        Args:
            voice_id: 语音ID
            
        Returns:
            语音信息
        """
        url = f"{self.base_url}/voices/{voice_id}"
        
        headers = {
            "Accept": "application/json",
            "xi-api-key": self.config.api_key
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"获取语音信息失败: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"获取语音信息异常: {str(e)}")
            return None

# 创建全局实例
voice_service = VoiceService()