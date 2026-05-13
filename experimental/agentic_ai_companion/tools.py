"""工具定义与执行，含 process_response_with_tools。"""

from __future__ import annotations

import json
import time
import wave
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from langsmith.run_helpers import trace
from loguru import logger
from google.genai.errors import ClientError
from pydantic import BaseModel, ConfigDict, Field

from app.core.companion_harness.tools.runtime import process_single_tool_call

_THIS_DIR = Path(__file__).resolve().parent
DATA_DIR = _THIS_DIR / "tmp"
APP_ICON_PATH = _THIS_DIR / "app_icon.png"
ZUN_LONG_PHOTO_PATH = _THIS_DIR / "尊龙.png"
COMPANION_PROFILE_DIR = _THIS_DIR / "companion_profile"

RECENT_MESSAGES_FOR_IMAGE = 10
RECENT_MESSAGES_FOR_LIVE = 10
RECENT_MESSAGES_FOR_SCENE = 10

# 内存维护已发送图片路径，用于 send_selfie_photo 去重
_sent_image_paths: set[str] = set()


def reset_sent_image_paths() -> None:
    """REPL 会话开始时调用，清空已发送图片列表。"""
    _sent_image_paths.clear()


WAV_SAMPLE_RATE = 24000
WAV_CHANNELS = 1
WAV_SAMPLE_WIDTH = 2


class ToolType(Enum):
    UNSPECIFIED = "unspecified"
    TERMINAL = "terminal"


class ToolContextType(Enum):
    NONE = "none"
    GEMINI_CLIENT = "gemini_client"
    GEMINI_CLIENT_WITH_MESSAGES = "gemini_client_with_messages"
    GEMINI_CLIENT_WITH_MESSAGES_AND_SYSTEM = "gemini_client_with_messages_and_system"
    GEMINI_CLIENT_WITH_MESSAGES_AND_NAMES = "gemini_client_with_messages_and_names"


class ProcessedResponse(BaseModel):
    """单轮 API 响应处理结果。"""

    model_config = ConfigDict(frozen=True)

    messages: list[dict[str, Any]]
    content: str | None = None
    done: bool
    assistant_text: str
    image_path: str | None = None
    tool_result: str | None = None


class ToolDefinition(BaseModel):
    """单条工具定义：API schema 与执行函数，由 TOOL_DEFINITIONS 统一维护。executor 仅运行时使用，不参与序列化。"""

    name: str
    description: str
    parameters: dict[str, Any]
    type: ToolType = ToolType.UNSPECIFIED
    context_type: ToolContextType = ToolContextType.NONE
    executor: Callable[..., tuple[str, str | None]] = Field(exclude=True)


def execute_send_app_icon(*, _logger=None) -> tuple[str, str | None]:
    """执行发送图片：校验 app_icon.png 存在。返回 (供 API 的结果字符串, 成功时为可点击的绝对路径否则 None)。"""
    if _logger is not None:
        _logger.info("执行 send_app_icon 工具，图片路径: %s", APP_ICON_PATH)
    if not APP_ICON_PATH.exists():
        if _logger is not None:
            _logger.warning("send_app_icon 失败: 图片文件不存在")
        return ("send_app_icon: Failed. Image file not found.", None)
    try:
        APP_ICON_PATH.read_bytes()
    except OSError as e:
        if _logger is not None:
            _logger.warning("send_app_icon 失败: 无法读取图片, error=%s", e)
        return (f"send_app_icon: Failed to read image ({e!s}).", None)
    path_str = str(APP_ICON_PATH.resolve())
    if _logger is not None:
        _logger.info("send_app_icon 成功，已返回路径: %s", path_str)
    return ("send_app_icon: Image sent.", path_str)


def execute_send_zun_long_photo(*, _logger=None) -> tuple[str, str | None]:
    """执行发送尊龙照片：校验 尊龙.png 存在。返回 (供 API 的结果字符串, 成功时为可点击的绝对路径否则 None)。"""
    if _logger is not None:
        _logger.info("执行 send_zun_long_photo 工具，图片路径: %s", ZUN_LONG_PHOTO_PATH)
    if not ZUN_LONG_PHOTO_PATH.exists():
        if _logger is not None:
            _logger.warning("send_zun_long_photo 失败: 图片文件不存在")
        return ("send_zun_long_photo: Failed. Image file not found.", None)
    try:
        ZUN_LONG_PHOTO_PATH.read_bytes()
    except OSError as e:
        if _logger is not None:
            _logger.warning("send_zun_long_photo 失败: 无法读取图片, error=%s", e)
        return (f"send_zun_long_photo: Failed to read image ({e!s}).", None)
    path_str = str(ZUN_LONG_PHOTO_PATH.resolve())
    if _logger is not None:
        _logger.info("send_zun_long_photo 成功，已返回路径: %s", path_str)
    return ("send_zun_long_photo: Image sent.", path_str)


def _list_companion_photos() -> list[Path]:
    """返回 companion_profile 中所有图片路径（顶层 + photos/ + photo_album/），按文件名排序。"""
    paths: list[Path] = []
    for ext in ("*.jpg", "*.jpeg", "*.png"):
        paths.extend(COMPANION_PROFILE_DIR.glob(ext))
    for subdir in ("photos", "photo_album"):
        d = COMPANION_PROFILE_DIR / subdir
        if d.is_dir():
            for ext in ("*.jpg", "*.jpeg", "*.png"):
                paths.extend(d.glob(ext))
    paths.sort(key=lambda p: p.name)
    return paths


def get_photo_album_index() -> dict[str, str]:
    """返回 companion_profile 相册索引：文件名（无后缀） -> 绝对路径。"""
    index: dict[str, str] = {}
    for p in _list_companion_photos():
        stem = p.stem
        if stem in index:
            continue
        try:
            p.read_bytes()
        except OSError:
            continue
        index[stem] = str(p.resolve())
    return index


def execute_send_selfie_photo(*, _logger=None) -> tuple[str, str | None]:
    """从 companion_profile 相册选取未发送过的图片发送。若全部已发送则返回文案、无路径。"""
    if _logger is not None:
        _logger.info("执行 send_selfie_photo 工具")
    candidates = _list_companion_photos()
    if not candidates:
        if _logger is not None:
            _logger.warning("send_selfie_photo 失败: companion_profile 中无图片")
        return ("send_selfie_photo: No photos available in album.", None)
    for p in candidates:
        path_str = str(p.resolve())
        if path_str not in _sent_image_paths:
            try:
                p.read_bytes()
            except OSError as e:
                if _logger is not None:
                    _logger.warning("send_selfie_photo 跳过无法读取的文件 %s: %s", p, e)
                continue
            if _logger is not None:
                _logger.info("send_selfie_photo 成功，已返回路径: %s", path_str)
            return ("send_selfie_photo: Photo sent.", path_str)
    if _logger is not None:
        _logger.info("send_selfie_photo: 所有相册图片已发送，返回文案")
    return ("send_selfie_photo: Already shared all my photos with you.", None)


def execute_generate_image(
    *,
    messages: list[dict[str, Any]],
    client: Any,
    input: str | None = None,
    char_name: str = "",
    user_name: str = "",
    ai_reference_image: str | None = None,
    user_reference_image: str | None = None,
    _logger=None,
    **kwargs: Any,
) -> tuple[str, str | None]:
    """根据工具参数 input 或对话上下文生成图片并写入本地文件，返回 (结果文案, 可点击绝对路径或 None)。"""
    from .chat_image_gen import (
        GenerateImageToolInput,
        generate_image_with_chat_to_image_behavior,
    )

    recent = (
        messages[-RECENT_MESSAGES_FOR_IMAGE:]
        if len(messages) > RECENT_MESSAGES_FOR_IMAGE
        else messages
    )
    scene_description = (input or "").strip()
    try:
        result = generate_image_with_chat_to_image_behavior(
            client=client,
            input_data=GenerateImageToolInput(
                scene_description=scene_description,
                messages=recent,
                char_name=char_name,
                user_name=user_name,
                ai_reference_image=ai_reference_image,
                user_reference_image=user_reference_image,
            ),
        )
        if _logger is not None:
            _logger.info(
                "generate_image 成功 status=%s image=%s metadata=%s",
                result.status,
                result.image_path,
                result.metadata_path,
            )
        tool_message = result.tool_message
        if result.metadata_path:
            tool_message = f"{tool_message} metadata={result.metadata_path}"
        return (tool_message, result.image_path)
    except (
        ClientError,
        ValueError,
        OSError,
        AttributeError,
        RuntimeError,
        TypeError,
    ) as e:
        if _logger is not None:
            _logger.warning("generate_image 失败: %s", e)
        return (f"generate_image: Failed ({e}).", None)


def execute_text_to_speech(
    text: str, *, client: Any, _logger=None, **kwargs: Any
) -> tuple[str, str | None]:
    """将文本转为语音并写入 WAV 文件，返回 (结果文案, 可点击绝对路径或 None)。"""
    from .speech_gen import generate_speech_from_text

    if not (text or "").strip():
        return ("text_to_speech: Text cannot be empty.", None)
    try:
        pcm = generate_speech_from_text(text.strip(), client=client)
    except (ValueError, OSError, AttributeError) as e:
        if _logger is not None:
            _logger.warning("text_to_speech 失败: %s", e)
        attempted = (text or "").strip()
        return (f"text_to_speech: Failed ({e}). Spoken (attempted): {attempted}", None)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / f"generated_speech_{int(time.time() * 1000)}.wav"
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(WAV_CHANNELS)
        wf.setsampwidth(WAV_SAMPLE_WIDTH)
        wf.setframerate(WAV_SAMPLE_RATE)
        wf.writeframes(pcm)
    path_str = str(out_path.resolve())
    if _logger is not None:
        _logger.info("text_to_speech 成功，已写入: %s", path_str)
    # 显示原文以便用户知道朗读内容（保留换行，不截断）
    spoken_preview = (text or "").strip()
    result_msg = f"text_to_speech: Speech generated. Spoken:\n{spoken_preview}"
    return (result_msg, path_str)


def execute_live_voice_message_reply(
    text: str,
    *,
    messages: list[dict[str, Any]],
    system_instruction: Any,
    _logger=None,
    **kwargs: Any,
) -> tuple[str, str | None]:
    """使用 Live API 生成语音回复并写入 WAV，返回 (结果文案, 可点击绝对路径或 None)。内部使用 Live 专用 client（v1beta），不依赖传入的 client。"""
    if _logger is not None:
        _logger.info(
            "live_voice_message_reply 输入参数: text=%s, messages=%s, system_instruction=%s",
            text,
            messages,
            system_instruction,
        )
    import asyncio

    from .live_voice_message import generate_speech_via_live

    if not (text or "").strip():
        return ("live_voice_message_reply: Text cannot be empty.", None)
    try:
        pcm, transcript = asyncio.run(
            generate_speech_via_live(
                text.strip(),
                messages=messages,
                system_instruction=system_instruction,
            )
        )
    except (ValueError, OSError, AttributeError, asyncio.TimeoutError) as e:
        if _logger is not None:
            _logger.warning("live_voice_message_reply 失败: %s", e)
        return (f"live_voice_message_reply: Failed ({e}).", None)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / f"live_voice_{int(time.time() * 1000)}.wav"
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(WAV_CHANNELS)
        wf.setsampwidth(WAV_SAMPLE_WIDTH)
        wf.setframerate(WAV_SAMPLE_RATE)
        wf.writeframes(pcm)
    path_str = str(out_path.resolve())
    if _logger is not None:
        _logger.info("live_voice_message_reply 成功，已写入: %s", path_str)
    # Path is shown once via image_path (new_pending) in REPL; do not embed in result to avoid double print
    if transcript:
        result = (
            f'live_voice_message_reply: Speech generated. Transcript: "{transcript}".'
        )
    else:
        result = "live_voice_message_reply: Speech generated. Transcript: (none)."
    return (result, path_str)


def execute_erotic_scene_generate(
    *,
    messages: list[dict[str, Any]],
    client: Any,
    char_name: str,
    user_name: str,
    user_desires: str,
    _logger=None,
    **kwargs: Any,
) -> tuple[str, str | None]:
    """根据最近对话与角色/用户名生成连续文字 scene，仅文本、不生成图片。返回 (结果文案含 scene 正文, None)。"""
    from .scene_gen import generate_erotic_scene_text

    if _logger is not None:
        _logger.info(
            "erotic_scene_generate: messages_count=%d char=%s user=%s",
            len(messages),
            char_name,
            user_name,
        )
    try:
        text = generate_erotic_scene_text(
            messages=messages,
            client=client,
            char_name=char_name,
            user_name=user_name,
            user_desires=user_desires or "",
            recent_n=RECENT_MESSAGES_FOR_SCENE,
            _logger=_logger,
        )
    except (ValueError, OSError, AttributeError) as e:
        if _logger is not None:
            _logger.warning("erotic_scene_generate 失败: %s", e)
        return (f"erotic_scene_generate: Failed ({e}).", None)
    result_msg = "erotic_scene_generate: Scene:\n" + (text or "").strip()
    if _logger is not None:
        _logger.info("erotic_scene_generate 成功，scene 长度=%d", len(text or ""))
    return (result_msg, None)


def build_tool_definitions(*, _logger=None) -> list[ToolDefinition]:
    """构建 TOOL_DEFINITIONS，注入 logger 到各 executor。"""

    def exec_send_app_icon(**kw):
        return execute_send_app_icon(_logger=_logger)

    def exec_send_zun_long(**kw):
        return execute_send_zun_long_photo(_logger=_logger)

    def exec_send_selfie(**kw):
        return execute_send_selfie_photo(_logger=_logger)

    def exec_gen_image(
        *,
        messages,
        client,
        input=None,
        char_name="",
        user_name="",
        ai_reference_image=None,
        user_reference_image=None,
        **kw,
    ):
        return execute_generate_image(
            messages=messages,
            client=client,
            input=input,
            char_name=char_name,
            user_name=user_name,
            ai_reference_image=ai_reference_image,
            user_reference_image=user_reference_image,
            _logger=_logger,
        )

    def exec_tts(*, text, client, **kw):
        return execute_text_to_speech(text=text, client=client, _logger=_logger)

    def exec_live_voice(*, text, messages, system_instruction, **kw):
        return execute_live_voice_message_reply(
            text=text,
            messages=messages,
            system_instruction=system_instruction,
            _logger=_logger,
        )

    def exec_love_making_scene_writer(
        *, messages, client, char_name, user_name, user_desires="", **kw
    ):
        return execute_erotic_scene_generate(
            messages=messages,
            client=client,
            char_name=char_name,
            user_name=user_name,
            user_desires=user_desires or "",
            _logger=_logger,
        )

    return [
        ToolDefinition(
            name="send_app_icon",
            description="Send the app icon image to the user (fixed file app_icon.png). When the user explicitly asks for app icon, picture, or icon, you MUST call this tool. Text-only replies cannot actually send images. Trigger phrases: send me app icon, app icon please, send app icon.",
            parameters={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            type=ToolType.TERMINAL,
            context_type=ToolContextType.NONE,
            executor=exec_send_app_icon,
        ),
        ToolDefinition(
            name="send_zun_long_photo",
            description="Send Zun Long's photo to the user (fixed file 尊龙.png). When the user asks for Zun Long, Zun Long's picture, or similar, you MUST call this tool. Text-only replies cannot actually send images. Trigger phrases: zun long picture, zun long's picture.",
            parameters={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            type=ToolType.TERMINAL,
            context_type=ToolContextType.NONE,
            executor=exec_send_zun_long,
        ),
        ToolDefinition(
            name="send_selfie_photo",
            description="Send a selfie/photo from AI Companion's album to the user. When the user asks for your photo, selfie, picture of you, show me you, send me a photo, etc., you MUST call this tool. The tool automatically avoids sending the same photo twice in the same conversation. Trigger phrases: your photo, selfie, picture of you, show me you, send me a photo.",
            parameters={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            type=ToolType.TERMINAL,
            context_type=ToolContextType.NONE,
            executor=exec_send_selfie,
        ),
        ToolDefinition(
            # generate_image is non-TERMINAL: after execution LLM continues to output text (e.g. interpretation or emotion) for the generated image.
            name="generate_image",
            description=(
                "Generate an intimacy role-play scene image using chat context and reference photos. "
                "Input should describe the fantasized scene between the user and the AI companion. "
                "The tool automatically uses AI/user profile images as references."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "input": {
                        "type": "string",
                        "description": "Scene description of the intimacy role-play that should be visualized.",
                    },
                    "ai_reference_image": {
                        "type": "string",
                        "description": "Optional override path to AI reference image.",
                    },
                    "user_reference_image": {
                        "type": "string",
                        "description": "Optional override path to user reference image.",
                    },
                },
                "additionalProperties": False,
            },
            context_type=ToolContextType.GEMINI_CLIENT_WITH_MESSAGES_AND_NAMES,
            type=ToolType.TERMINAL,
            executor=exec_gen_image,
        ),
        ToolDefinition(
            name="text_to_speech",
            description=(
                "Convert text to speech. Call this **only** when the user's **current** message explicitly asks for voice or speech, e.g. 'say something', 'speak to me', 'I want to hear you', 'send a voice message', 'read aloud', 'say X'. "
                "Do NOT call this tool for normal conversational replies (e.g. user said 'wow', 'how are you', 'of course', 'I saw your project')."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Include non-audible descriptions like scene, thoughts, actions, etc., which are in parentheses (), and actual dialogue that is not inside parentheses ().",
                    }
                },
                "required": ["text"],
                "additionalProperties": False,
            },
            type=ToolType.TERMINAL,
            context_type=ToolContextType.GEMINI_CLIENT,
            executor=exec_tts,
        ),
        ToolDefinition(
            name="love_making_scene_writer",
            description=(
                "Write a love making scene between the character and the user. "
                "Call this tool when:\n"
                "- the user shows intention to make love with you\n"
                "- you or the user started a love making interaction\n"
                "- the user is sexually aroused\n"
                "- they explicitly ask for a love making scene or story\n"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "user_desires": {
                        "type": "string",
                        "description": "The desires of the user. Describe the user's desires in detail.",
                    }
                },
                "additionalProperties": False,
            },
            type=ToolType.TERMINAL,
            context_type=ToolContextType.GEMINI_CLIENT_WITH_MESSAGES_AND_NAMES,
            executor=exec_love_making_scene_writer,
        ),
        # This tool is right now only useful for generating erotic voice messages.
        # But it's too slow, and the effect is no different from text_to_speech.
        # ToolDefinition(
        #     name="live_voice_message_reply",
        #     description=(
        #         "Strong emotional but slower voice message reply using Live API with full context. Use only when the user wants strong emotional stimulus, explicitly asks for a 'Live' or 'conversational' voice reply; for all other voice requests (say something, hear you, voice message, read aloud, etc.) use text_to_speech instead, which is faster."
        #     ),
        #     parameters={
        #         "type": "object",
        #         "properties": {
        #             "text": {
        #                 "type": "string",
        #                 "description": "The reply content to speak in this voice message.",
        #             }
        #         },
        #         "required": ["text"],
        #         "additionalProperties": False,
        #     },
        #     type=ToolType.TERMINAL,
        #     context_type=ToolContextType.GEMINI_CLIENT_WITH_MESSAGES_AND_SYSTEM,
        #     executor=exec_live_voice,
        # ),
    ]


def _build_tool_context(
    context_type: ToolContextType,
    new_messages: list[dict[str, Any]],
    get_gemini_client,
    *,
    build_system_messages=None,
    char_name: str | None = None,
    user_name: str | None = None,
) -> dict[str, Any]:
    """根据 ToolContextType 构建注入 executor 的 context_kwargs。"""
    if context_type == ToolContextType.GEMINI_CLIENT_WITH_MESSAGES_AND_SYSTEM:
        from google.genai import types as genai_types

        system_instruction = genai_types.Content(
            parts=[genai_types.Part.from_text(text=".")],
            role="user",
        )
        if (
            build_system_messages is not None
            and char_name is not None
            and user_name is not None
        ):
            system_msgs = build_system_messages(char_name, user_name)
            merged = "\n\n".join(
                (m.get("content") or "").strip()
                for m in system_msgs
                if m.get("role") == "system"
            ).strip()
            if merged:
                system_instruction = genai_types.Content(
                    parts=[genai_types.Part.from_text(text=merged)],
                    role="user",
                )
        return {
            "client": get_gemini_client(),
            "messages": new_messages[-RECENT_MESSAGES_FOR_LIVE:],
            "system_instruction": system_instruction,
        }
    if context_type == ToolContextType.GEMINI_CLIENT_WITH_MESSAGES_AND_NAMES:
        return {
            "client": get_gemini_client(),
            "messages": new_messages[-RECENT_MESSAGES_FOR_SCENE:],
            "char_name": char_name or "",
            "user_name": user_name or "",
        }
    if context_type == ToolContextType.GEMINI_CLIENT_WITH_MESSAGES:
        return {
            "client": get_gemini_client(),
            "messages": new_messages[-RECENT_MESSAGES_FOR_IMAGE:],
        }
    if context_type == ToolContextType.GEMINI_CLIENT:
        return {"client": get_gemini_client()}
    return {}


def process_response_with_tools(
    messages: list[dict[str, Any]],
    message: Any,
    *,
    tool_executors: dict[str, Callable[..., tuple[str, str | None]]],
    tool_types: dict[str, ToolType],
    tool_context_types: dict[str, ToolContextType],
    get_gemini_client,
    _logger=None,
    build_system_messages=None,
    char_name: str | None = None,
    user_name: str | None = None,
) -> ProcessedResponse:
    """
    处理单轮 API 响应中的 tool_call：执行工具并追加 assistant + tool 消息，按 TERMINAL 返回 content/done。
    调用方必须保证 message 含有且仅含一个 tool_call；无 tool_calls 时由 run_repl 直接处理。
    """

    def get_tool_context(
        context_type: ToolContextType, new_messages: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return _build_tool_context(
            context_type,
            new_messages,
            get_gemini_client,
            build_system_messages=build_system_messages,
            char_name=char_name,
            user_name=user_name,
        )

    def is_terminal_tool(tool_type: Any) -> bool:
        return tool_type == ToolType.TERMINAL

    runtime_out = process_single_tool_call(
        messages=messages,
        message=message,
        tool_executors=tool_executors,
        tool_types=tool_types,
        tool_context_types=tool_context_types,
        get_tool_context=get_tool_context,
        is_terminal_tool=is_terminal_tool,
        unknown_tool_message=lambda name: f"未知工具: {name}",
    )

    image_path_sent = runtime_out.image_path
    result = runtime_out.tool_result
    assistant_content = runtime_out.assistant_text
    if image_path_sent:
        _sent_image_paths.add(image_path_sent)
    if _logger is not None:
        tool_name = getattr(message.tool_calls[0].function, "name", "<unknown>")
        _logger.info("工具 %s 执行完毕，result 长度=%d", tool_name, len(result))

    content = (assistant_content + "\n" + result).strip() if runtime_out.done else None
    return ProcessedResponse(
        messages=runtime_out.messages,
        content=content,
        done=runtime_out.done,
        assistant_text=assistant_content,
        image_path=image_path_sent,
        tool_result=result,
    )
