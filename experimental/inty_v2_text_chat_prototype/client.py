"""单次 chat.completions 调用（内层，不拼业务 system）。"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

_DEFAULT_MODEL = "deepseek/deepseek-v3.2"

_CLIENT: OpenAI | None = None


def _ensure_dotenv() -> None:
    load_dotenv()


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


def complete(messages: list[dict[str, Any]], *, model: str | None = None) -> str:
    m = model or default_model()
    client = get_client()
    resp = client.chat.completions.create(model=m, messages=messages)
    content = resp.choices[0].message.content
    return content if content is not None else ""
