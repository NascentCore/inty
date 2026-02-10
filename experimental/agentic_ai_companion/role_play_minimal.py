"""
最小化 Role Play 示例：仅用 app/core/agent/prompts + prompt_template 组装系统消息，OpenAI SDK 多轮对话。
与 Agent.build_system_messages 的组装方式一致，不依赖 Agent/DB/config。
CREATED_BY_AGENT
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# 尽早加载 .env（显式路径，避免工作目录影响）
_THIS_DIR = Path(__file__).resolve().parent
_ENV_PATH = _THIS_DIR / ".env"
if _ENV_PATH.exists():
    from dotenv import load_dotenv
    load_dotenv(_ENV_PATH)

from app.core.agent import prompt_template, prompts
from openai import OpenAI


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL_OPENROUTER = "openai/gpt-4o-mini"
DEFAULT_MODEL_OPENAI = "gpt-4o-mini"

CHAR_NAME = "小艾"
USER_NAME = "User"


def build_system_messages_openai(char_name: str, user_name: str) -> list[dict[str, str]]:
    """
    使用 prompts.py 的主/模式提示词与 prompt_template 渲染，组装 OpenAI 格式的系统消息列表。
    与 Agent.build_system_messages 的组装方式一致（仅 main + mode，无角色卡/时间等）。
    """
    main_prompt = prompts.PURITY_ROLEPLAY_PROMPT.main_prompt
    mode_prompt = prompts.PURITY_ROLEPLAY_PROMPT.mode_prompt
    rendered_main = prompt_template.render_prompt_jinja2_template(
        main_prompt, char=char_name, user=user_name
    )
    rendered_mode = prompt_template.render_prompt_jinja2_template(
        mode_prompt, char=char_name, user=user_name
    )
    return [
        {"role": "system", "content": rendered_main},
        {"role": "system", "content": rendered_mode},
    ]


def create_openai_client() -> OpenAI:
    """优先使用 OPENROUTER_API_KEY，否则使用 OPENAI_API_KEY。"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        return OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return OpenAI(api_key=api_key)
    print("错误：请设置 OPENROUTER_API_KEY 或 OPENAI_API_KEY（可在 .env 中配置）", file=sys.stderr)
    sys.exit(1)


def get_default_model() -> str:
    if os.getenv("OPENROUTER_API_KEY"):
        return os.getenv("OPENROUTER_DEFAULT_MODEL", DEFAULT_MODEL_OPENROUTER)
    return os.getenv("OPENAI_DEFAULT_MODEL", DEFAULT_MODEL_OPENAI)


def run_repl(
    char_name: str = CHAR_NAME,
    user_name: str = USER_NAME,
    model: str | None = None,
) -> None:
    """终端内多轮 role play：读用户输入 → 调用 API → 打印助手回复。"""
    system_messages = build_system_messages_openai(char_name, user_name)
    client = create_openai_client()
    if model is None:
        model = get_default_model()
    messages: list[dict[str, str]] = [*system_messages]
    print(f"角色: {char_name} | 用户: {user_name} | 模型: {model}")
    print("输入内容后回车发送，空行或 Ctrl+C 退出。\n")
    while True:
        try:
            line = input(f"{user_name}> ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not line:
            break
        messages.append({"role": "user", "content": line})
        resp = client.chat.completions.create(model=model, messages=messages)
        content = (resp.choices[0].message.content or "").strip()
        messages.append({"role": "assistant", "content": content})
        print(f"{char_name}> {content}\n")


def main() -> None:
    run_repl()


if __name__ == "__main__":
    main()
