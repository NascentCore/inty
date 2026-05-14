# 调用 Gemini API TTS 将文本转为语音（PCM），不写文件、不依赖 role_play_minimal。
# 参考: https://ai.google.dev/gemini-api/docs/speech-generation

from __future__ import annotations

from typing import TYPE_CHECKING

from langsmith.run_helpers import traceable

if TYPE_CHECKING:
    from google.genai import Client

TTS_MODEL = "gemini-2.5-flash-preview-tts"
from loguru import logger

MAX_TEXT_LENGTH = 2000

# 与 live_voice.DEFAULT_VOICE_NAME 保持相同，保证 text_to_speech 与 live_voice_message_reply 音色一致
DEFAULT_VOICE_NAME = "Kore"

# 发给 TTS 的指令：识别 role-play 格式（括号内为舞台说明），只读台词并参考场景语气
TTS_ROLEPLAY_INSTRUCTION = (
    "You are a voice actor. "
    "You are naturally and convincingly acting out a scene description.\n\n"
    "In the scene description: "
    "non-audible descriptions, like directions, thoughts, actions, etc., are in parentheses (); "
    "the rest are the actual dialogue that you must speak. "
    "example: <begin-of-example>(whispering) I won the lottery!!!.<end-of-example>\n\n"
    "You must:\n"
    "1. In your speech: use the non-audible descriptions to inform the delivery, "
    "strictly adhere to the non-audible descriptions.\n"
    "2. Never speak the non-audible descriptions\n"
    "3. Speak only the actual dialogue that is not inside parentheses ()\n\n"
    "The following are the scene description:\n\n"
)


def _trace_output_pcm(data: bytes | None) -> dict:
    """process_outputs：避免将原始 PCM 字节写入 trace，仅记录摘要。异常时 data 可能为 None。"""
    if data is None:
        return {"status": "error", "pcm_bytes": 0}
    return {"pcm_bytes": len(data), "status": "success"}


# [tracing] LangSmith 中对应 role_play_minimal 的「text_to_speech」工具调用；输出摘要由 process_outputs 记录
@traceable(
    name="text_to_speech",
    run_type="tool",
    process_outputs=_trace_output_pcm,
)
def generate_speech_from_text(
    text: str,
    client: "Client",
    voice_name: str = DEFAULT_VOICE_NAME,
    model: str = TTS_MODEL,
) -> bytes:
    """
    将文本通过 Gemini TTS 转为单说话人语音，返回 PCM 字节（24kHz, 1ch, 16-bit）。
    client 由调用方传入（通常为 LangSmith wrapped 的 genai.Client）。
    """
    from google.genai import types

    raw_text = (text or "").strip()
    if not raw_text:
        raise ValueError("要朗读的文本不能为空")
    if len(raw_text) > MAX_TEXT_LENGTH:
        raw_text = raw_text[:MAX_TEXT_LENGTH]

    contents = TTS_ROLEPLAY_INSTRUCTION + raw_text
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
    logger.info(
        "TTS API 请求: model=%s voice_name=%s contents 长度=%d 请求内容: %s",
        model,
        voice_name,
        len(contents),
        contents,
    )
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
