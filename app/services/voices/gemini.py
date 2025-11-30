"""
Gemini 语音生成提供商
封装 Gemini TTS API 调用和音频处理逻辑
"""

# CREATED_BY_AGENT

import io
import struct
import wave
from typing import Any, Optional, Tuple

from google import genai
from google.genai import types
from loguru import logger
from mutagen.mp3 import MP3

from app.core.config import GeminiVoiceConfig


def _parse_audio_mime_type(mime_type: str) -> Tuple[int, int]:
    """解析音频 MIME 类型，提取采样率和位深度"""
    sample_rate = 24000
    bits_per_sample = 16
    parts = [part.strip() for part in mime_type.split(";")]
    for part in parts:
        if part.lower().startswith("rate="):
            try:
                sample_rate = int(part.split("=", 1)[1])
            except (ValueError, IndexError):
                pass
        if part.lower().startswith("audio/l"):
            try:
                bits_per_sample = int(part.split("l", 1)[1])
            except (ValueError, IndexError):
                pass
    return sample_rate, bits_per_sample


def _pcm_to_wav(
    audio_data: bytes, sample_rate: int, bits_per_sample: int, num_channels: int = 1
) -> bytes:
    """将 PCM 音频数据转换为 WAV 格式"""
    bytes_per_sample = bits_per_sample // 8
    byte_rate = sample_rate * num_channels * bytes_per_sample
    block_align = num_channels * bytes_per_sample
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + len(audio_data),
        b"WAVE",
        b"fmt ",
        16,
        1,
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        len(audio_data),
    )
    return header + audio_data


def _calculate_pcm_duration(
    audio_data: bytes, sample_rate: int, bits_per_sample: int, num_channels: int = 1
) -> float:
    """计算 PCM 音频数据的时长"""
    if sample_rate <= 0 or bits_per_sample <= 0 or num_channels <= 0:
        return 0.0
    bytes_per_second = sample_rate * num_channels * (bits_per_sample // 8)
    if bytes_per_second == 0:
        return 0.0
    return len(audio_data) / bytes_per_second


def _extract_inline_audio_part(response: Any) -> Optional[Any]:
    """从 Gemini API 响应中提取内联音频部分"""
    candidates = getattr(response, "candidates", []) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if not content or not getattr(content, "parts", None):
            continue
        for part in content.parts:
            if getattr(part, "inline_data", None):
                return part
    return None


class GeminiVoiceProvider:
    """Gemini 语音生成提供商"""

    LANGUAGE_CODE_ALIAS = {
        "zh": "cmn-CN",
        "en": "en-US",
    }

    def __init__(self, config: GeminiVoiceConfig):
        self.config = config
        self._client: Optional[genai.Client] = None

    def _get_client(self) -> genai.Client:
        """获取 Gemini 客户端（懒加载）"""
        if self._client is None:
            client_kwargs: dict[str, Any] = {}
            if self.config.api_key:
                client_kwargs["api_key"] = self.config.api_key
            self._client = genai.Client(**client_kwargs)
        return self._client

    def resolve_language_code(self, language: str) -> Optional[str]:
        """解析语言代码，支持别名转换"""
        lang_key = (language or "").lower()
        if lang_key in self.LANGUAGE_CODE_ALIAS:
            return self.LANGUAGE_CODE_ALIAS[lang_key]
        return self.config.default_language_code

    def normalize_audio(
        self, audio_data: bytes, mime_type: str
    ) -> Optional[Tuple[bytes, float, str, str]]:
        """
        标准化 Gemini 返回的音频格式

        Returns:
            (音频数据, 时长(秒), content_type, 文件扩展名)
        """
        mime = (mime_type or "").lower()
        if mime.startswith("audio/l"):
            sample_rate, bits_per_sample = _parse_audio_mime_type(mime_type)
            wav_bytes = _pcm_to_wav(audio_data, sample_rate, bits_per_sample)
            duration = _calculate_pcm_duration(audio_data, sample_rate, bits_per_sample)
            return wav_bytes, duration, "audio/wav", ".wav"
        if "wav" in mime or "wave" in mime:
            duration = self._calculate_wav_duration(audio_data)
            return audio_data, duration, "audio/wav", ".wav"
        if "mpeg" in mime or "mp3" in mime:
            duration = self._calculate_audio_duration(audio_data)
            return audio_data, duration, "audio/mpeg", ".mp3"

        sample_rate, bits_per_sample = _parse_audio_mime_type("audio/L16;rate=24000")
        wav_bytes = _pcm_to_wav(audio_data, sample_rate, bits_per_sample)
        duration = _calculate_pcm_duration(audio_data, sample_rate, bits_per_sample)
        return wav_bytes, duration, "audio/wav", ".wav"

    def _calculate_wav_duration(self, audio_data: bytes) -> float:
        """计算 WAV 音频的时长"""
        try:
            with wave.open(io.BytesIO(audio_data), "rb") as wav_file:
                frames = wav_file.getnframes()
                frame_rate = wav_file.getframerate()
                if frame_rate == 0:
                    return 0.0
                return frames / frame_rate
        except Exception as e:
            logger.error(f"计算WAV音频时长失败: {str(e)}")
            return 0.0

    def _calculate_audio_duration(self, audio_data: bytes) -> float:
        """计算音频数据的时长（MP3）"""
        try:
            audio_file = io.BytesIO(audio_data)
            audio = MP3(audio_file)
            return audio.info.length
        except Exception as e:
            logger.error(f"计算音频时长失败: {str(e)}")
            return 0.0

    async def generate_voice(
        self, text: str, voice_name: str, model: str, language: str
    ) -> Optional[Tuple[bytes, float, str, str]]:
        """
        调用 Gemini TTS API 生成语音

        Args:
            text: 要转换的文本
            voice_name: Gemini 音色名称
            model: 模型名称
            language: 语言代码

        Returns:
            (音频数据, 时长(秒), content_type, 文件扩展名) 或 None
        """
        if not self.config.enabled:
            return None

        try:
            client = self._get_client()
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=text),
                    ],
                )
            ]
            speech_config = types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                ),
                language_code=self.resolve_language_code(language),
            )
            generate_config = types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=speech_config,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
            )

            logger.debug(
                f"调用Gemini语音模型: voice_name={voice_name}, model={model}, text_length={len(text)}"
            )
            response = client.models.generate_content(
                model=model, contents=contents, config=generate_config
            )
            inline_part = _extract_inline_audio_part(response)
            if (
                inline_part is None
                or inline_part.inline_data is None
                or not inline_part.inline_data.data
            ):
                logger.error("Gemini 语音生成未返回音频数据")
                return None

            audio_bytes = inline_part.inline_data.data
            mime_type = inline_part.inline_data.mime_type or "audio/L16;rate=24000"
            normalized = self.normalize_audio(audio_bytes, mime_type)
            if not normalized:
                return None

            logger.debug(
                f"Gemini 语音生成成功，mime_type={mime_type}, 大小={len(audio_bytes)} bytes"
            )
            return normalized
        except Exception as e:
            logger.error(f"Gemini 语音生成失败: {str(e)}")
            logger.exception("Gemini 语音生成异常详细信息:")
            return None

