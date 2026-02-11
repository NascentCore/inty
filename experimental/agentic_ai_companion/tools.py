"""工具定义与执行，含 process_response_with_tools。"""

from __future__ import annotations

import json
import time
import wave
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field

_THIS_DIR = Path(__file__).resolve().parent
APP_ICON_PATH = _THIS_DIR / "app_icon.png"
ZUN_LONG_PHOTO_PATH = _THIS_DIR / "尊龙.png"

RECENT_MESSAGES_FOR_IMAGE = 10

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


class ProcessedResponse(BaseModel):
    """单轮 API 响应处理结果。"""
    model_config = ConfigDict(frozen=True)

    messages: list[dict[str, Any]]
    content: str | None
    done: bool
    assistant_text: str
    image_path: str | None


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
        return ("发送失败：图片文件不存在。", None)
    try:
        APP_ICON_PATH.read_bytes()
    except OSError as e:
        if _logger is not None:
            _logger.warning("send_app_icon 失败: 无法读取图片, error=%s", e)
        return (f"发送失败：无法读取图片（{e!s}）。", None)
    path_str = str(APP_ICON_PATH.resolve())
    if _logger is not None:
        _logger.info("send_app_icon 成功，已返回路径: %s", path_str)
    return ("已发送图片。", path_str)


def execute_send_zun_long_photo(*, _logger=None) -> tuple[str, str | None]:
    """执行发送尊龙照片：校验 尊龙.png 存在。返回 (供 API 的结果字符串, 成功时为可点击的绝对路径否则 None)。"""
    if _logger is not None:
        _logger.info("执行 send_zun_long_photo 工具，图片路径: %s", ZUN_LONG_PHOTO_PATH)
    if not ZUN_LONG_PHOTO_PATH.exists():
        if _logger is not None:
            _logger.warning("send_zun_long_photo 失败: 图片文件不存在")
        return ("发送失败：图片文件不存在。", None)
    try:
        ZUN_LONG_PHOTO_PATH.read_bytes()
    except OSError as e:
        if _logger is not None:
            _logger.warning("send_zun_long_photo 失败: 无法读取图片, error=%s", e)
        return (f"发送失败：无法读取图片（{e!s}）。", None)
    path_str = str(ZUN_LONG_PHOTO_PATH.resolve())
    if _logger is not None:
        _logger.info("send_zun_long_photo 成功，已返回路径: %s", path_str)
    return ("已发送图片。", path_str)


def execute_generate_image(
    *,
    messages: list[dict[str, Any]],
    client: Any,
    _logger=None,
    **kwargs: Any,
) -> tuple[str, str | None]:
    """根据当前对话上下文（最近 N 条消息）生成图片并写入本地文件，返回 (结果文案, 可点击绝对路径或 None)。"""
    from .image_gen import generate_image_from_messages

    recent = messages[-RECENT_MESSAGES_FOR_IMAGE:] if len(messages) > RECENT_MESSAGES_FOR_IMAGE else messages
    try:
        image_bytes = generate_image_from_messages(recent, client=client)
    except (ValueError, OSError, AttributeError) as e:
        if _logger is not None:
            _logger.warning("generate_image 失败: %s", e)
        return (f"生成失败：{e}", None)
    suffix = ".jpg"
    if image_bytes[:2] == b"\xff\xd8":
        suffix = ".jpg"
    elif image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        suffix = ".png"
    out_path = _THIS_DIR / f"generated_{int(time.time() * 1000)}{suffix}"
    out_path.write_bytes(image_bytes)
    path_str = str(out_path.resolve())
    if _logger is not None:
        _logger.info("generate_image 成功，已写入: %s", path_str)
    return ("已根据对话上下文生成图片。", path_str)


def execute_text_to_speech(text: str, *, client: Any, _logger=None, **kwargs: Any) -> tuple[str, str | None]:
    """将文本转为语音并写入 WAV 文件，返回 (结果文案, 可点击绝对路径或 None)。"""
    from .speech_gen import generate_speech_from_text

    if not (text or "").strip():
        return ("要朗读的文本不能为空。", None)
    try:
        pcm = generate_speech_from_text(text.strip(), client=client)
    except (ValueError, OSError, AttributeError) as e:
        if _logger is not None:
            _logger.warning("text_to_speech 失败: %s", e)
        return (f"生成失败：{e}", None)
    out_path = _THIS_DIR / f"generated_speech_{int(time.time() * 1000)}.wav"
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(WAV_CHANNELS)
        wf.setsampwidth(WAV_SAMPLE_WIDTH)
        wf.setframerate(WAV_SAMPLE_RATE)
        wf.writeframes(pcm)
    path_str = str(out_path.resolve())
    if _logger is not None:
        _logger.info("text_to_speech 成功，已写入: %s", path_str)
    return ("已生成语音。", path_str)


def build_tool_definitions(*, _logger=None) -> list[ToolDefinition]:
    """构建 TOOL_DEFINITIONS，注入 logger 到各 executor。"""
    def exec_send_app_icon(**kw):
        return execute_send_app_icon(_logger=_logger)
    def exec_send_zun_long(**kw):
        return execute_send_zun_long_photo(_logger=_logger)
    def exec_gen_image(*, messages, client, **kw):
        return execute_generate_image(messages=messages, client=client, _logger=_logger)
    def exec_tts(*, text, client, **kw):
        return execute_text_to_speech(text=text, client=client, _logger=_logger)

    return [
        ToolDefinition(
            name="send_app_icon",
            description="向用户发送应用图标图片（固定为 app_icon.png）。当用户明确要求发送图片、图标或 app icon 时，必须调用本工具，仅用文字回复无法真正发出图片。",
            parameters={"type": "object", "properties": {}, "additionalProperties": False},
            type=ToolType.TERMINAL,
            context_type=ToolContextType.NONE,
            executor=exec_send_app_icon,
        ),
        ToolDefinition(
            name="send_zun_long_photo",
            description="向用户发送尊龙照片（固定为 尊龙.png）。当用户要求看尊龙、尊龙照片或类似内容时，必须调用本工具，仅用文字回复无法真正发出图片。",
            parameters={"type": "object", "properties": {}, "additionalProperties": False},
            type=ToolType.TERMINAL,
            context_type=ToolContextType.NONE,
            executor=exec_send_zun_long,
        ),
        ToolDefinition(
            # generate_image 为 non-TERMINAL：执行后继续让 LLM 根据生成的图片输出文字（如解读或情感表达），提升体验。
            name="generate_image",
            description="根据当前对话上下文生成一张图片。仅在用户已说明想要什么图（主题、风格、场景等）时才调用本工具；调用时无需参数，系统会使用当前聊天 session 中最近的 10 条消息作为上下文生成图片。若用户只说「生成一张图」「画一张图」「generate a new image」等而无具体描述，不要先调用本工具，应先简短追问用户想要什么（如主题、风格、氛围），待用户补充后再调用；仅用文字回复无法真正发出图片。",
            parameters={"type": "object", "properties": {}, "additionalProperties": False},
            context_type=ToolContextType.GEMINI_CLIENT_WITH_MESSAGES,
            executor=exec_gen_image,
        ),
        ToolDefinition(
            name="text_to_speech",
            description="将指定文本转为语音并发送给用户。当用户要求用语音回复、朗读、用语音说、或使用英文表达如 say X / say something / speak X / speak to me / I want to hear your voice / say it out loud 时，必须调用本工具。例如用户说 say \"how are you\" 或「用语音说你好」时，应调用本工具并传入要读出的台词，仅用文字回复无法真正发出语音。参数 text 必须是**仅要读出的台词**（例如「你好」或「Hello」），不要传入动作或舞台说明（如 (looks at you)、(smiles)）。",
            parameters={
                "type": "object",
                "properties": {"text": {"type": "string", "description": "要朗读的纯台词内容，仅限实际说出的文字，不要包含括号内的动作描述"}},
                "required": ["text"],
                "additionalProperties": False,
            },
            type=ToolType.TERMINAL,
            context_type=ToolContextType.GEMINI_CLIENT,
            executor=exec_tts,
        ),
    ]


def _build_tool_context(
    context_type: ToolContextType,
    new_messages: list[dict[str, Any]],
    get_gemini_client,
) -> dict[str, Any]:
    """根据 ToolContextType 构建注入 executor 的 context_kwargs。"""
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
) -> ProcessedResponse:
    """
    处理单轮 API 响应中的 tool_call：执行工具并追加 assistant + tool 消息，按 TERMINAL 返回 content/done。
    调用方必须保证 message 含有且仅含一个 tool_call；无 tool_calls 时由 run_repl 直接处理。
    """
    raw_tool_calls = getattr(message, "tool_calls", None) or []
    assert len(raw_tool_calls) >= 1, "process_response_with_tools 仅在有 tool_calls 时调用"
    assert len(raw_tool_calls) <= 1, "工具调用数量必须为 0 或 1，因为禁止 parallel_tool_calls"
    tool_call = raw_tool_calls[0]
    assistant_content = (message.content or "").strip()
    tc_dict: dict[str, Any] = {
        "id": tool_call.id,
        "type": getattr(tool_call, "type", "function"),
        "function": {
            "name": tool_call.function.name,
            "arguments": tool_call.function.arguments or "",
        },
    }
    assistant_msg = {
        "role": "assistant",
        "content": message.content or "",
        "tool_calls": [tc_dict],
    }
    new_messages = [*messages, assistant_msg]

    name = tool_call.function.name
    raw_args = tool_call.function.arguments or ""
    try:
        parsed_args = json.loads(raw_args) if raw_args.strip() else {}
    except json.JSONDecodeError:
        parsed_args = {}
    context_type = tool_context_types.get(name, ToolContextType.NONE)
    context_kwargs = _build_tool_context(context_type, new_messages, get_gemini_client)

    executor = tool_executors.get(name)
    if executor:
        result, path = executor(**parsed_args, **context_kwargs)
        image_path_sent = path
    else:
        result = f"未知工具: {name}"
        image_path_sent = None
    new_messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})
    if _logger is not None:
        _logger.info("工具 %s 执行完毕，result 长度=%d", name, len(result))

    if tool_types.get(name, ToolType.UNSPECIFIED) == ToolType.TERMINAL:
        content = (assistant_content + "\n" + result).strip()
        return ProcessedResponse(messages=new_messages, content=content, done=True, assistant_text=assistant_content, image_path=image_path_sent)
    return ProcessedResponse(messages=new_messages, content=None, done=False, assistant_text=assistant_content, image_path=image_path_sent)
