# 调用 Gemini API TTS 将文本转为语音（PCM），不写文件、不依赖 role_play_minimal。
# 参考: https://ai.google.dev/gemini-api/docs/speech-generation

from __future__ import annotations

import logging
import os

TTS_MODEL = "gemini-2.5-flash-preview-tts"
logger = logging.getLogger(__name__)
MAX_TEXT_LENGTH = 2000

# 发给 TTS 的指令：识别 role-play 格式（括号内为舞台说明），只读台词并参考场景语气
TTS_ROLEPLAY_INSTRUCTION = (
    "The following is role-play style content. Lines or phrases in parentheses () are stage "
    "directions or actions — do not speak them; only speak the actual dialogue. Use the mood or "
    "scenario in the directions to inform your tone and delivery. Now read the following:\n\n"
)


def generate_speech_from_text(
    text: str,
    voice_name: str = "Kore",
    model: str = TTS_MODEL,
) -> bytes:
    """
    将文本通过 Gemini TTS 转为单说话人语音，返回 PCM 字节（24kHz, 1ch, 16-bit）。
    使用 GEMINI_API_KEY（.env），不在此模块内写 WAV 文件。
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or not api_key.strip():
        raise ValueError("GEMINI_API_KEY 未设置，请在 .env 中配置")

    from google import genai
    from google.genai import types

    raw_text = (text or "").strip()
    if not raw_text:
        raise ValueError("要朗读的文本不能为空")
    if len(raw_text) > MAX_TEXT_LENGTH:
        raw_text = raw_text[:MAX_TEXT_LENGTH]

    contents = TTS_ROLEPLAY_INSTRUCTION + raw_text

    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=voice_name,
                )
            )
        ),
    )
    logger.info("TTS API 请求: model=%s voice_name=%s contents 长度=%d 请求内容: %s", model, voice_name, len(contents), contents)
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        raise ValueError("Gemini TTS 未返回 candidates")
    content = getattr(candidates[0], "content", None)
    if not content:
        raise ValueError("Gemini TTS 返回的 candidate 无 content")
    parts = getattr(content, "parts", None) or []
    if not parts:
        raise ValueError("Gemini TTS 返回的 content 无 parts")
    inline = getattr(parts[0], "inline_data", None)
    if not inline:
        raise ValueError("Gemini TTS 返回的 part 无 inline_data")
    data = getattr(inline, "data", None)
    if not isinstance(data, bytes) or len(data) == 0:
        raise ValueError("Gemini TTS 返回的音频数据为空或格式不可用")
    return data
