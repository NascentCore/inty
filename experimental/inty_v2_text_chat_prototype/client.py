"""单次 chat.completions 调用（内层，不拼业务 system）。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

_DEFAULT_MODEL = "deepseek/deepseek-v3.2"

_CLIENT: OpenAI | None = None

# experimental/inty_v2_text_chat_prototype/client.py → parents[2] = inty repo root
_REPO_ROOT_FOR_DOTENV = Path(__file__).resolve().parent.parent.parent


def load_prototype_dotenv() -> None:
    """Load `inty/.env` first, then cwd `.env`, so keys like `FAL_KEY` work when cwd is not repo root."""
    load_dotenv(_REPO_ROOT_FOR_DOTENV / ".env")
    load_dotenv()


def _ensure_dotenv() -> None:
    load_prototype_dotenv()


def get_client() -> OpenAI:
    global _CLIENT
    _ensure_dotenv()
    if _CLIENT is not None:
        return _CLIENT
    key = (os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        raise ValueError(
            "Missing API key: set OPENROUTER_API_KEY or OPENAI_API_KEY in the environment "
            "(or a .env file loaded by python-dotenv)."
        )
    if os.getenv("OPENROUTER_API_KEY"):
        _CLIENT = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=key,
        )
    else:
        _CLIENT = OpenAI(api_key=key)
    return _CLIENT


def default_model() -> str:
    _ensure_dotenv()
    return os.getenv("INTY_V2_PROTO_MODEL", _DEFAULT_MODEL)


def memory_model() -> str:
    _ensure_dotenv()
    return os.getenv("INTY_V2_PROTO_MEMORY_MODEL") or default_model()


def day_summary_model() -> str:
    """当日总结性记忆（memory/YYYY-MM-DD.md）；可与长期 MEMORY 策展使用不同模型。"""
    _ensure_dotenv()
    return os.getenv("INTY_V2_PROTO_DAY_SUMMARY_MODEL") or memory_model()


def soul_model() -> str:
    """SOUL.md 策展（边界与价值观落盘）；默认与记忆策展同模型。"""
    _ensure_dotenv()
    return os.getenv("INTY_V2_PROTO_SOUL_MODEL") or memory_model()


def user_model() -> str:
    """USER.md 策展（用户对助手可见的长期画像）；默认与记忆策展同模型。"""
    _ensure_dotenv()
    return os.getenv("INTY_V2_PROTO_USER_MODEL") or memory_model()


def complete(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    llm_trace: bool = False,
    trace_where: str = "complete",
    ws_label: str,
    trace_day: str,
) -> str:
    m = model or default_model()
    client = get_client()
    resp = client.chat.completions.create(model=m, messages=messages)
    if llm_trace:
        from .llm_trace import emit_trace, summarize_completion_response, summarize_messages

        emit_trace(
            trace_where,
            round_idx=1,
            model=m,
            messages=summarize_messages(
                messages,
                ws_label=ws_label,
                trace_day=trace_day,
            ),
            response=summarize_completion_response(resp),
        )
    content = resp.choices[0].message.content
    return content if content is not None else ""
