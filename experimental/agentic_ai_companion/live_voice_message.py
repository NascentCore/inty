# Live API 单轮语音生成：系统指令 + 最近 N 条消息 + 回复文案 → PCM。
# 代码参考: experimental/agentic_ai_companion/code_samples/erotic_actress_gemini_live_camera.py
# 潜在优势：
# - 生成速度省去一次调用 text 生成、tts 的等待，但是实际生成来看还是比生成文本然后 tts 要慢
# - 可以更有表现力？目前还没有具体测试
# 潜在问题：
# - 是否会有更严格的审核？


from __future__ import annotations

import asyncio
import os
from typing import Any

from google import genai
from google.genai import types

# 与 speech_gen.DEFAULT_VOICE_NAME 保持相同，保证两工具音色一致
DEFAULT_VOICE_NAME = "Kore"

LIVE_MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"
LIVE_TIMEOUT_SECONDS = 30


# Live API 需要 http_options={"api_version": "v1beta"}，与 get_gemini_client() 可能不同，故在模块内自建
def _live_client() -> genai.Client:
    return genai.Client(
        http_options={"api_version": "v1beta"},
        api_key=os.environ.get("GEMINI_API_KEY"),
    )


def _format_messages_as_context(messages: list[dict[str, Any]], recent_n: int) -> str:
    """将最近 N 条 user/assistant 消息格式化为对话上下文字符串。"""
    lines: list[str] = []
    for m in messages[-recent_n:]:
        role = m.get("role", "")
        content = (m.get("content") or "").strip()
        # 任意角色（user、assistant、tool 等）的空消息均跳过，避免 Live API 收到畸形的 "User: " / "Assistant: " 行。
        if not content:
            continue
        if role == "user":
            lines.append(f"User: {content}")
        elif role == "assistant":
            lines.append(f"Assistant: {content}")
    return "\n".join(lines) if lines else ""


def _system_instruction_to_content(
    system_instruction: types.Content | str,
) -> types.Content:
    """将 str 或 Content 转为 Live 所需的 types.Content。"""
    if isinstance(system_instruction, types.Content):
        return system_instruction
    return types.Content(
        parts=[types.Part.from_text(text=(system_instruction or "").strip() or ".")],
        role="user",
    )


async def generate_speech_via_live(
    text: str,
    messages: list[dict[str, Any]],
    system_instruction: types.Content | str,
    voice_name: str = DEFAULT_VOICE_NAME,
    model: str = LIVE_MODEL,
    recent_n: int = 10,
) -> tuple[bytes, str]:
    """
    使用 Gemini Live API 生成单段语音：带系统指令与最近 N 条消息上下文，发送本轮回复文案，收齐音频与转录文本。
    返回 (PCM 字节 24kHz 1ch 16-bit, 转录文本)；无转录时 transcript 为空字符串。
    内部始终使用带 v1beta 的 client，不接收外部 client 参数。
    """
    text = (text or "").strip() or "."
    sys_content = _system_instruction_to_content(system_instruction)
    context_str = _format_messages_as_context(messages, recent_n)
    if context_str:
        payload = f"Recent conversation:\n{context_str}\n\nReply in a short voice message:\n{text}"
    else:
        payload = text

    # Live API 需要 v1beta，统一使用模块内 client
    live_client = _live_client()
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
            )
        ),
        context_window_compression=types.ContextWindowCompressionConfig(
            trigger_tokens=25600,
            sliding_window=types.SlidingWindow(target_tokens=12800),
        ),
        system_instruction=sys_content,
        output_audio_transcription=types.AudioTranscriptionConfig(),
    )

    chunks: list[bytes] = []
    transcript_parts: list[str] = []

    async def _run() -> None:
        nonlocal chunks, transcript_parts
        async with live_client.aio.live.connect(model=model, config=config) as session:
            await session.send(input=payload, end_of_turn=True)
            turn = session.receive()
            async for response in turn:
                sc = getattr(response, "server_content", None)
                if data := getattr(response, "data", None):
                    if isinstance(data, bytes):
                        chunks.append(data)
                piece = getattr(response, "text", None)
                if piece and isinstance(piece, str):
                    transcript_parts.append(piece)
                if sc and getattr(sc, "output_transcription", None):
                    ot = getattr(sc.output_transcription, "text", None)
                    if ot and isinstance(ot, str):
                        transcript_parts.append(ot)

    await asyncio.wait_for(_run(), timeout=LIVE_TIMEOUT_SECONDS)
    if not chunks:
        raise ValueError("Live API 未返回音频数据")
    transcript = "".join(transcript_parts).strip()
    return (b"".join(chunks), transcript)
