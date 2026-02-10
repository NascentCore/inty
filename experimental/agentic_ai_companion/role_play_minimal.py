from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

# 尽早加载 .env（显式路径，避免工作目录影响）
_THIS_DIR = Path(__file__).resolve().parent
_ENV_PATH = _THIS_DIR / ".env"
assert _ENV_PATH.exists(), f"环境变量文件不存在: {_ENV_PATH}"
from dotenv import load_dotenv
load_dotenv(_ENV_PATH)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

from app.core.agent import prompt_template, prompts
from openai import OpenAI


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "google/gemini-2.5-flash-lite"

CHAR_NAME = "AI Companion"
USER_NAME = "User"

APP_ICON_PATH = _THIS_DIR / "app_icon.png"

SEND_IMAGE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "send_image",
            "description": "向用户发送应用图标图片（固定为 app_icon.png）。当用户明确要求发送图片、图标或 app icon 时，必须调用本工具，仅用文字回复无法真正发出图片。",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
]


assert os.getenv("OPENROUTER_API_KEY") is not None, "OPENROUTER_API_KEY 未设置"


def execute_send_image() -> tuple[str, str | None]:
    """执行发送图片：校验 app_icon.png 存在。返回 (供 API 的结果字符串, 成功时为可点击的绝对路径否则 None)。"""
    logger.info("执行 send_image 工具，图片路径: %s", APP_ICON_PATH)
    if not APP_ICON_PATH.exists():
        logger.warning("send_image 失败: 图片文件不存在")
        return ("发送失败：图片文件不存在。", None)
    try:
        APP_ICON_PATH.read_bytes()
    except OSError as e:
        logger.warning("send_image 失败: 无法读取图片, error=%s", e)
        return (f"发送失败：无法读取图片（{e!s}）。", None)
    path_str = str(APP_ICON_PATH.resolve())
    logger.info("send_image 成功，已返回路径: %s", path_str)
    return ("已发送图片。", path_str)


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
) -> tuple[list[dict[str, Any]], str | None, bool, str, str | None]:
    """
    处理单轮 API 响应：若含 tool_calls 则执行并追加 assistant + tool 消息，返回 (新 messages, None, False, 助手文本, 本轮发送的图片路径)；
    若无 tool_calls 则返回 (未追加的 messages, content, True, "", None)。
    """
    tool_calls = getattr(message, "tool_calls", None) or []
    if not tool_calls:
        content = (message.content or "").strip()
        logger.info("API 响应无 tool_calls，content 长度=%d", len(content))
        return (messages, content, True, "", None)
    tool_names = [getattr(tc.function, "name", "") for tc in tool_calls]
    logger.info("API 响应含 tool_calls: %s，助手文本长度=%d", tool_names, len((message.content or "")))
    assistant_content = (message.content or "").strip()
    assistant_msg: dict[str, Any] = {
        "role": "assistant",
        "content": message.content or "",
        "tool_calls": [
            {
                "id": tc.id,
                "type": getattr(tc, "type", "function"),
                "function": {"name": tc.function.name, "arguments": tc.function.arguments or ""},
            }
            for tc in tool_calls
        ],
    }
    new_messages = [*messages, assistant_msg]
    image_path_sent: str | None = None
    for tc in tool_calls:
        if tc.function.name == "send_image":
            result, path = execute_send_image()
            if path is not None:
                image_path_sent = path
        else:
            result = f"未知工具: {tc.function.name}"
        new_messages.append(
            {"role": "tool", "tool_call_id": tc.id, "content": result}
        )
        logger.info("工具 %s 执行完毕，result 长度=%d", tc.function.name, len(result))
    logger.info("本轮 tool 处理完成，messages 总数=%d，image_path_sent=%s", len(new_messages), image_path_sent is not None)
    return (new_messages, None, False, assistant_content, image_path_sent)


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
    print("输入内容后回车发送，空行或 Ctrl+C 退出。\n")
    turn = 0
    while True:
        try:
            line = input(f"{user_name}> ").strip()
        except (KeyboardInterrupt, EOFError):
            logger.info("用户中断或 EOF，退出 REPL")
            break
        if not line:
            logger.info("用户输入空行，退出 REPL")
            break
        turn += 1
        logger.info("第 %d 轮对话，用户输入长度=%d: %s", turn, len(line), line[:80] + ("..." if len(line) > 80 else ""))
        messages.append({"role": "user", "content": line})
        pending_image_path: str | None = None
        round_num = 0
        while True:
            round_num += 1
            logger.info("API 请求 第 %d 轮 turn=%d，messages 条数=%d", round_num, turn, len(messages))
            resp = client.chat.completions.create(
                model=model, messages=messages, tools=SEND_IMAGE_TOOLS
            )
            msg = resp.choices[0].message
            has_tool_calls = bool(getattr(msg, "tool_calls", None))
            logger.info("API 响应 第 %d 轮，has_tool_calls=%s", round_num, has_tool_calls)
            messages, content, done, assistant_text, image_path = process_response_with_tools(
                messages, msg
            )
            if image_path is not None:
                pending_image_path = image_path
            if done:
                assert content is not None
                messages.append({"role": "assistant", "content": content})
                display = content if content else "（已通过 send_image 发送图片。）"
                if pending_image_path:
                    display = f"{display}\n点击打开: {pending_image_path}"
                logger.info("第 %d 轮对话结束，assistant content 长度=%d，附带图片路径=%s", turn, len(content), pending_image_path is not None)
                print(f"{char_name}> {display}\n")
                break
            if assistant_text:
                print(f"{char_name}> {assistant_text}")
            logger.debug("继续本轮 API 请求，messages 已追加 assistant + tool")


def main() -> None:
    logger.info("入口 main() 调用 run_repl")
    run_repl()
    logger.info("run_repl 已退出")
