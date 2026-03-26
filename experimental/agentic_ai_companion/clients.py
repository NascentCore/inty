"""OpenRouter 与 Gemini API 客户端，由 role_play_minimal 组装后供 repl、tools 使用。"""

from __future__ import annotations

import os
from typing import Any

from langsmith import wrappers
from openai import OpenAI

from app.core.agentic_kernel.providers.facade import (
    OpenAICompatibleClientOptions,
    get_openai_compatible_sync_client,
)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

_gemini_client: Any | None = None


def create_openai_client() -> OpenAI:
    return get_openai_compatible_sync_client(
        OpenAICompatibleClientOptions(
            base_url=OPENROUTER_BASE_URL,
            api_key=os.getenv("OPENROUTER_API_KEY"),
            wrap_langsmith=True,
            chat_name="AgenticAICompanion_Chat",
            completions_name="AgenticAICompanion",
            use_fake_openai=False,
        )
    )


def _create_gemini_client():
    from google import genai

    base = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    wrap_fn = getattr(wrappers, "wrap_gemini", None)
    if wrap_fn is not None:
        return wrap_fn(
            base,
            tracing_extra={
                "tags": ["agentic-ai-companion", "gemini"],
                "metadata": {"source": "experimental"},
            },
            chat_name="AgenticAICompanion_Gemini",
        )
    return base


def get_gemini_client():
    """懒加载单例，避免每次工具调用都新建 client。"""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = _create_gemini_client()
    return _gemini_client
