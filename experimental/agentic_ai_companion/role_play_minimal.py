from __future__ import annotations

import os
import sys
from pathlib import Path

# 尽早加载 .env（显式路径，避免工作目录影响）
_THIS_DIR = Path(__file__).resolve().parent
_ENV_PATH = _THIS_DIR / ".env"
assert _ENV_PATH.exists(), f"环境变量文件不存在: {_ENV_PATH}"
from dotenv import load_dotenv
load_dotenv(_ENV_PATH)

from app.core.agent import prompt_template, prompts
from openai import OpenAI


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "google/gemini-2.5-flash-lite"

CHAR_NAME = "AI Companion"
USER_NAME = "User"


assert os.getenv("OPENROUTER_API_KEY") is not None, "OPENROUTER_API_KEY 未设置"

def build_system_messages_openai(char_name: str, user_name: str) -> list[dict[str, str]]:
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
    return OpenAI(base_url=OPENROUTER_BASE_URL, api_key=os.getenv("OPENROUTER_API_KEY"))


def run_repl(
    char_name: str = CHAR_NAME,
    user_name: str = USER_NAME,
    model: str = OPENROUTER_MODEL,
) -> None:
    system_messages = build_system_messages_openai(char_name, user_name)
    client = create_openai_client()
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
