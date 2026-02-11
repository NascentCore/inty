from __future__ import annotations

import json
import logging
import os
import time
import wave
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Callable

import cyclopts

from pydantic import BaseModel, ConfigDict, Field

EMPTY_RESPONSE = "(E.M.P.T.Y.)"

# 尽早加载 .env（显式路径，避免工作目录影响）
_THIS_DIR = Path(__file__).resolve().parent
_ENV_PATH = _THIS_DIR / ".env"
assert _ENV_PATH.exists(), f"环境变量文件不存在: {_ENV_PATH}"
from dotenv import load_dotenv
load_dotenv(_ENV_PATH)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_real_logger = logging.getLogger(__name__)


class _LoggerWrapper:
    """包装器：当 enabled=False 时所有 logger.* 调用不输出，用于 --debug=false 减少屏幕干扰。"""

    def __init__(self, real: logging.Logger, enabled: bool = False) -> None:
        self._real = real
        self._enabled = enabled

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def _log(self, level: str, msg: str, *args: Any, **kwargs: Any) -> None:
        if self._enabled:
            getattr(self._real, level)(msg, *args, **kwargs, stacklevel=3)

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log("debug", msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log("info", msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log("warning", msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log("error", msg, *args, **kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log("critical", msg, *args, **kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        if self._enabled:
            self._real.exception(msg, *args, **kwargs, stacklevel=3)


logger: _LoggerWrapper = _LoggerWrapper(_real_logger, enabled=False)

from app.core.agent import prompt_template, prompts
from openai import OpenAI


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "google/gemini-2.5-flash"

CHAR_NAME = "AI Companion"
USER_NAME = "Yaxiong Zhao"

APP_ICON_PATH = _THIS_DIR / "app_icon.png"
ZUN_LONG_PHOTO_PATH = _THIS_DIR / "尊龙.png"

assert os.getenv("OPENROUTER_API_KEY") is not None, "OPENROUTER_API_KEY 未设置"


class ToolType(Enum):
    UNSPECIFIED = "unspecified"
    TERMINAL = "terminal"


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
    executor: Callable[..., tuple[str, str | None]] = Field(exclude=True)


def execute_send_app_icon() -> tuple[str, str | None]:
    """执行发送图片：校验 app_icon.png 存在。返回 (供 API 的结果字符串, 成功时为可点击的绝对路径否则 None)。"""
    logger.info("执行 send_app_icon 工具，图片路径: %s", APP_ICON_PATH)
    if not APP_ICON_PATH.exists():
        logger.warning("send_app_icon 失败: 图片文件不存在")
        return ("发送失败：图片文件不存在。", None)
    try:
        APP_ICON_PATH.read_bytes()
    except OSError as e:
        logger.warning("send_app_icon 失败: 无法读取图片, error=%s", e)
        return (f"发送失败：无法读取图片（{e!s}）。", None)
    path_str = str(APP_ICON_PATH.resolve())
    logger.info("send_app_icon 成功，已返回路径: %s", path_str)
    return ("已发送图片。", path_str)


def execute_send_zun_long_photo() -> tuple[str, str | None]:
    """执行发送尊龙照片：校验 尊龙.png 存在。返回 (供 API 的结果字符串, 成功时为可点击的绝对路径否则 None)。"""
    logger.info("执行 send_zun_long_photo 工具，图片路径: %s", ZUN_LONG_PHOTO_PATH)
    if not ZUN_LONG_PHOTO_PATH.exists():
        logger.warning("send_zun_long_photo 失败: 图片文件不存在")
        return ("发送失败：图片文件不存在。", None)
    try:
        ZUN_LONG_PHOTO_PATH.read_bytes()
    except OSError as e:
        logger.warning("send_zun_long_photo 失败: 无法读取图片, error=%s", e)
        return (f"发送失败：无法读取图片（{e!s}）。", None)
    path_str = str(ZUN_LONG_PHOTO_PATH.resolve())
    logger.info("send_zun_long_photo 成功，已返回路径: %s", path_str)
    return ("已发送图片。", path_str)


RECENT_MESSAGES_FOR_IMAGE = 10


def execute_generate_image(
    *,
    messages: list[dict[str, Any]],
    **kwargs: Any,
) -> tuple[str, str | None]:
    """根据当前对话上下文（最近 N 条消息）生成图片并写入本地文件，返回 (结果文案, 可点击绝对路径或 None)。"""
    from .image_gen import generate_image_from_messages

    recent = messages[-RECENT_MESSAGES_FOR_IMAGE:] if len(messages) > RECENT_MESSAGES_FOR_IMAGE else messages
    try:
        image_bytes = generate_image_from_messages(recent)
    except Exception as e:
        logger.warning("generate_image 失败: %s", e)
        return (f"生成失败：{e}", None)
    suffix = ".jpg"
    if image_bytes[:2] == b"\xff\xd8":
        suffix = ".jpg"
    elif image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        suffix = ".png"
    out_path = _THIS_DIR / f"generated_{int(time.time() * 1000)}{suffix}"
    out_path.write_bytes(image_bytes)
    path_str = str(out_path.resolve())
    logger.info("generate_image 成功，已写入: %s", path_str)
    return ("已根据对话上下文生成图片。", path_str)


WAV_SAMPLE_RATE = 24000
WAV_CHANNELS = 1
WAV_SAMPLE_WIDTH = 2


def execute_text_to_speech(text: str, **kwargs: Any) -> tuple[str, str | None]:
    """将文本转为语音并写入 WAV 文件，返回 (结果文案, 可点击绝对路径或 None)。"""
    from .speech_gen import generate_speech_from_text

    if not (text or "").strip():
        return ("要朗读的文本不能为空。", None)
    try:
        pcm = generate_speech_from_text(text.strip())
    except Exception as e:
        logger.warning("text_to_speech 失败: %s", e)
        return (f"生成失败：{e}", None)
    out_path = _THIS_DIR / f"generated_speech_{int(time.time() * 1000)}.wav"
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(WAV_CHANNELS)
        wf.setsampwidth(WAV_SAMPLE_WIDTH)
        wf.setframerate(WAV_SAMPLE_RATE)
        wf.writeframes(pcm)
    path_str = str(out_path.resolve())
    logger.info("text_to_speech 成功，已写入: %s", path_str)
    return ("已生成语音。", path_str)


TOOL_DEFINITIONS: list[ToolDefinition] = [
    ToolDefinition(
        name="send_app_icon",
        description="向用户发送应用图标图片（固定为 app_icon.png）。当用户明确要求发送图片、图标或 app icon 时，必须调用本工具，仅用文字回复无法真正发出图片。",
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
        type=ToolType.TERMINAL,
        executor=execute_send_app_icon,
    ),
    ToolDefinition(
        name="send_zun_long_photo",
        description="向用户发送尊龙照片（固定为 尊龙.png）。当用户要求看尊龙、尊龙照片或类似内容时，必须调用本工具，仅用文字回复无法真正发出图片。",
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
        type=ToolType.TERMINAL,
        executor=execute_send_zun_long_photo,
    ),
    ToolDefinition(
        name="generate_image",
        description="根据当前对话上下文生成一张图片。仅在用户已说明想要什么图（主题、风格、场景等）时才调用本工具；调用时无需参数，系统会使用当前聊天 session 中最近的 10 条消息作为上下文生成图片。若用户只说「生成一张图」「画一张图」「generate a new image」等而无具体描述，不要先调用本工具，应先简短追问用户想要什么（如主题、风格、氛围），待用户补充后再调用；仅用文字回复无法真正发出图片。",
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
        # type=ToolType.TERMINAL,
        executor=execute_generate_image,
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
        executor=execute_text_to_speech,
    ),
]

TOOLS = [
    {"type": "function", "function": {"name": d.name, "description": d.description, "parameters": d.parameters}}
    for d in TOOL_DEFINITIONS
]
TOOL_EXECUTORS = {d.name: d.executor for d in TOOL_DEFINITIONS}
TOOL_TYPES = {d.name: d.type for d in TOOL_DEFINITIONS}


def build_system_messages_openai(char_name: str, user_name: str) -> list[dict[str, str]]:
    logger.debug("构建系统消息 char_name=%s user_name=%s", char_name, user_name)
    main_prompt = prompts.PURITY_ROLEPLAY_PROMPT.main_prompt
    mode_prompt = prompts.PURITY_ROLEPLAY_PROMPT.mode_prompt
    rendered_main = prompt_template.render_prompt_jinja2_template(
        main_prompt, char=char_name, user=user_name
    )
    rendered_mode = prompt_template.render_prompt_jinja2_template(
        mode_prompt, char=char_name, user=user_name
    )
    msgs = [
        {"role": "system", "content": rendered_main},
        {"role": "system", "content": rendered_mode},
    ]
    logger.info("系统消息已构建，共 %d 条", len(msgs))
    return msgs


def create_openai_client() -> OpenAI:
    return OpenAI(base_url=OPENROUTER_BASE_URL, api_key=os.getenv("OPENROUTER_API_KEY"))


def process_response_with_tools(
    messages: list[dict[str, Any]],
    message: Any,
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
    context_kwargs: dict[str, Any] = {}
    if name == "generate_image":
        context_kwargs["messages"] = new_messages[-RECENT_MESSAGES_FOR_IMAGE:]

    executor = TOOL_EXECUTORS.get(name)
    if executor:
        result, path = executor(**parsed_args, **context_kwargs)
        image_path_sent = path
    else:
        result = f"未知工具: {name}"
        image_path_sent = None
    new_messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})
    logger.info("工具 %s 执行完毕，result 长度=%d", name, len(result))

    # 按 OpenRouter/OpenAI 约定，响应中的 tool name 来自本次请求的 tools 列表（Tool Validation: name matching tool definition），故可直接用 TOOL_TYPES[name]。
    if TOOL_TYPES[name] == ToolType.TERMINAL:
        content = (assistant_content + "\n" + result).strip()
        return ProcessedResponse(messages=new_messages, content=content, done=True, assistant_text=assistant_content, image_path=image_path_sent)
    return ProcessedResponse(messages=new_messages, content=None, done=False, assistant_text=assistant_content, image_path=image_path_sent)


def run_repl(
    char_name: str = CHAR_NAME,
    user_name: str = USER_NAME,
    model: str = OPENROUTER_MODEL,
) -> None:
    logger.info("REPL 启动 char_name=%s user_name=%s model=%s", char_name, user_name, model)
    system_messages = build_system_messages_openai(char_name, user_name)
    client = create_openai_client()
    messages: list[dict[str, Any]] = [*system_messages]
    print(f"角色: {char_name} | 用户: {user_name} | 模型: {model}")
    print("输入内容后回车发送，空行跳过，Ctrl+C 退出。\n")
    turn = 0

    # 对话主循环：读取用户输入，构建 messages，发送 API 请求，处理响应。
    while True:
        try:
            line = input(f"{user_name}> ").strip()
        except (KeyboardInterrupt, EOFError):
            logger.info("用户中断或 EOF，退出 REPL")
            # TODO：实际中这个循环应该重新开始，持续进行对话，而不是终止。
            break
        if not line:
            logger.debug("空行跳过")
            continue

        turn += 1
        logger.info("第 %d 轮对话，用户输入长度=%d: %s", turn, len(line), line[:80] + ("..." if len(line) > 80 else ""))

        # 构建本轮 Chat Completion 请求的 messages，包括系统消息、用户消息、工具调用（若有）。
        messages.append({"role": "user", "content": line})
        pending_image_path: str | None = None
        
        # 执行本轮 Chat Completion：1) create；2) 无工具 → 返回；有工具 → TERMINAL 返回 / 非 TERMINAL 打印、执行、循环。
        round_num = 0
        while True:
            round_num += 1
            logger.info("API 请求 第 %d 轮 turn=%d，messages 条数=%d", round_num, turn, len(messages))
            logger.info("Current messages: %s", json.dumps(messages, indent=2))
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOLS,
                parallel_tool_calls=False,
            )
            _raw = resp.model_dump() if hasattr(resp, "model_dump") else repr(resp)
            logger.info("API raw response: %s", _raw)
            msg = resp.choices[0].message
            has_tool_calls = bool(getattr(msg, "tool_calls", None))
            logger.info("API 响应 第 %d 轮，has_tool_calls=%s", round_num, has_tool_calls)

            # 2.1 无工具调用 → 直接返回（此前若有非 TERMINAL 工具如 generate_image 已设置 pending_image_path，一并展示）
            if not has_tool_calls:
                raw = getattr(msg, "content", None)
                content = (raw if isinstance(raw, str) else "").strip()
                messages.append({"role": "assistant", "content": content})
                display = content or EMPTY_RESPONSE
                logger.info("第 %d 轮对话结束，assistant content 长度=%d，附带图片路径=%s", turn, len(content), pending_image_path is not None)
                print(f"{char_name}> {display}\n")
                if pending_image_path is not None:
                    print(f"{char_name}> {pending_image_path}\n")
                break

            # 2.2 有工具调用 → 按是否 TERMINAL 分叉
            tool_name = msg.tool_calls[0].function.name
            is_terminal = TOOL_TYPES.get(tool_name, ToolType.UNSPECIFIED) == ToolType.TERMINAL

            if is_terminal:
                # 2.2.1 TERMINAL：执行工具后返回
                logger.info("执行 TERMINAL 工具 %s，msg: %s", tool_name, json.dumps(msg.model_dump(), indent=2))
                out = process_response_with_tools(messages, msg)
                messages = out.messages
                if out.image_path is not None:
                    pending_image_path = out.image_path
                assert out.content is not None
                if messages[-1]["role"] == "user":
                    messages.append({"role": "assistant", "content": out.content})
                display = pending_image_path or out.content or EMPTY_RESPONSE
                logger.info("第 %d 轮对话结束，assistant content 长度=%d，附带图片路径=%s", turn, len(out.content), pending_image_path is not None)
                print(f"{char_name}> {display}\n")
                break

            # 2.2.2 非 TERMINAL：打印中间结果，执行工具，继续循环
            assistant_text = (msg.content or "").strip()
            if assistant_text:
                print(f"{char_name}> {assistant_text}\n")
            out = process_response_with_tools(messages, msg)
            messages = out.messages
            if out.image_path is not None:
                pending_image_path = out.image_path
            logger.debug("继续本轮 API 请求，messages 已追加 assistant + tool")


def main(
    debug: Annotated[
        bool,
        cyclopts.Parameter(name="--debug", help="开启时输出 logger 日志，默认关闭以减少屏幕干扰"),
    ] = False,
) -> None:
    logger.set_enabled(debug)
    if not debug:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
    logger.info("入口 main() 调用 run_repl")
    run_repl()
    logger.info("run_repl 已退出")
