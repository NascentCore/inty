# 调用 Gemini API TTS 将文本转为语音（PCM），不写文件、不依赖 role_play_minimal。
# 参考: https://ai.google.dev/gemini-api/docs/speech-generation

from __future__ import annotations

import os

TTS_MODEL = "gemini-2.5-flash-preview-tts"
MAX_TEXT_LENGTH = 2000


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

    clean_text = (text or "").strip()
    if not clean_text:
        raise ValueError("要朗读的文本不能为空")
    if len(clean_text) > MAX_TEXT_LENGTH:
        clean_text = clean_text[:MAX_TEXT_LENGTH]

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
    response = client.models.generate_content(
        model=model,
        contents=clean_text,
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
