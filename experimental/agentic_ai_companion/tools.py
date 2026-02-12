"""工具定义与执行，含 process_response_with_tools。"""

from __future__ import annotations

import json
import time
import wave
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from langsmith.run_helpers import trace
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


def execute_generate_image(
    *,
    messages: list[dict[str, Any]],
    client: Any,
    input: str | None = None,
    _logger=None,
    **kwargs: Any,
) -> tuple[str, str | None]:
    """根据工具参数 input 或对话上下文生成图片并写入本地文件，返回 (结果文案, 可点击绝对路径或 None)。"""
    from .image_gen import _prompt_from_messages, generate_image_from_messages

    recent = messages[-RECENT_MESSAGES_FOR_IMAGE:] if len(messages) > RECENT_MESSAGES_FOR_IMAGE else messages
    prompt = (input or "").strip() or _prompt_from_messages(recent)
    try:
        image_bytes = generate_image_from_messages(client=client, prompt=prompt)
    except (ValueError, OSError, AttributeError) as e:
        if _logger is not None:
            _logger.warning("generate_image 失败: %s", e)
        return (f"generate_image: Failed ({e}).", None)
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
    return ("generate_image: Image generated.", path_str)


def execute_text_to_speech(text: str, *, client: Any, _logger=None, **kwargs: Any) -> tuple[str, str | None]:
    """将文本转为语音并写入 WAV 文件，返回 (结果文案, 可点击绝对路径或 None)。"""
    from .speech_gen import generate_speech_from_text

    if not (text or "").strip():
        return ("text_to_speech: Text cannot be empty.", None)
    try:
        pcm = generate_speech_from_text(text.strip(), client=client)
    except (ValueError, OSError, AttributeError) as e:
        if _logger is not None:
            _logger.warning("text_to_speech 失败: %s", e)
        return (f"text_to_speech: Failed ({e}).", None)
    out_path = _THIS_DIR / f"generated_speech_{int(time.time() * 1000)}.wav"
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(WAV_CHANNELS)
        wf.setsampwidth(WAV_SAMPLE_WIDTH)
        wf.setframerate(WAV_SAMPLE_RATE)
        wf.writeframes(pcm)
    path_str = str(out_path.resolve())
    if _logger is not None:
        _logger.info("text_to_speech 成功，已写入: %s", path_str)
    return ("text_to_speech: Speech generated.", path_str)


def build_tool_definitions(*, _logger=None) -> list[ToolDefinition]:
    """构建 TOOL_DEFINITIONS，注入 logger 到各 executor。"""
    def exec_send_app_icon(**kw):
        return execute_send_app_icon(_logger=_logger)
    def exec_send_zun_long(**kw):
        return execute_send_zun_long_photo(_logger=_logger)
    def exec_gen_image(*, messages, client, input=None, **kw):
        return execute_generate_image(messages=messages, client=client, input=input, _logger=_logger)
    def exec_tts(*, text, client, **kw):
        return execute_text_to_speech(text=text, client=client, _logger=_logger)

    return [
        ToolDefinition(
            name="send_app_icon",
            description="Send the app icon image to the user (fixed file app_icon.png). When the user explicitly asks for app icon, picture, or icon, you MUST call this tool. Text-only replies cannot actually send images. Trigger phrases: send me app icon, app icon please, send app icon.",
            parameters={"type": "object", "properties": {}, "additionalProperties": False},
            type=ToolType.TERMINAL,
            context_type=ToolContextType.NONE,
            executor=exec_send_app_icon,
        ),
        ToolDefinition(
            name="send_zun_long_photo",
            description="Send Zun Long's photo to the user (fixed file 尊龙.png). When the user asks for Zun Long, Zun Long's picture, or similar, you MUST call this tool. Text-only replies cannot actually send images. Trigger phrases: zun long picture, zun long's picture.",
            parameters={"type": "object", "properties": {}, "additionalProperties": False},
            type=ToolType.TERMINAL,
            context_type=ToolContextType.NONE,
            executor=exec_send_zun_long,
        ),
        ToolDefinition(
            # generate_image is non-TERMINAL: after execution LLM continues to output text (e.g. interpretation or emotion) for the generated image.
            name="generate_image",
            description="Generate an image based on the input prompt. When the user requests an image, extract or summarize their description into the input parameter.",
            parameters={
                "type": "object",
                "properties": {
                    "input": {
                        "type": "string",
                        "description": "The image generation prompt. Describe the scene, subject, style. When the user requests an image, extract or summarize their description here.",
                    }
                },
                "additionalProperties": False,
            },
            context_type=ToolContextType.GEMINI_CLIENT_WITH_MESSAGES,
            type=ToolType.TERMINAL,
            executor=exec_gen_image,
        ),
        ToolDefinition(
            name="text_to_speech",
            description="Convert text to speech and send to the user. When the user asks for voice reply, read aloud, or says 'say X', 'speak X', 'say something', 'speak to me', 'I want to hear your voice', 'say it out loud', you MUST call this tool. The text parameter must be only the spoken lines, not actions or stage directions like (looks at you) or (smiles). Text-only replies cannot actually send voice.",
            parameters={
                "type": "object",
                "properties": {"text": {"type": "string", "description": "The spoken line content only; do not include action descriptions in parentheses."}},
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
        trace_inputs = {"tool_name": name}
        if "text" in parsed_args:
            trace_inputs["text_length"] = len(str(parsed_args.get("text", "")))
        if "input" in parsed_args:
            trace_inputs["input_length"] = len(str(parsed_args.get("input", "")))
        if "messages" in context_kwargs:
            trace_inputs["messages_count"] = len(context_kwargs.get("messages", []))
        with trace(
            name=f"tool_executor_{name}",
            run_type="tool",
            inputs=trace_inputs,
        ) as run:
            result, path = executor(**parsed_args, **context_kwargs)
            run.end(outputs={"result_length": len(result), "has_path": path is not None})
        image_path_sent = path
    else:
        result = f"未知工具: {name}"
        image_path_sent = None
    new_messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})
    if _logger is not None:
        _logger.info("工具 %s 执行完毕，result 长度=%d", name, len(result))

    if tool_types.get(name, ToolType.UNSPECIFIED) == ToolType.TERMINAL:
        content = (assistant_content + "\n" + result).strip()
        return ProcessedResponse(messages=new_messages, content=content, done=True, assistant_text=assistant_content, image_path=image_path_sent, tool_result=result)
    return ProcessedResponse(messages=new_messages, content=None, done=False, assistant_text=assistant_content, image_path=image_path_sent, tool_result=result)
