"""OpenRouter 与 Gemini API 客户端，由 role_play_minimal 组装后供 repl、tools 使用。"""

from __future__ import annotations

import os
from typing import Any
from openai import OpenAI

from app.core.companion_harness.providers.openai_compatible_clients import (
    OpenAICompatibleClientOptions,
    get_openai_compatible_sync_client,
)
from app.core.companion_harness.providers.gemini import (
    GeminiClientOptions,
    get_gemini_client as get_kernel_gemini_client,
)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

_gemini_client: Any | None = None


def create_openai_client() -> OpenAI:
    """返回按配置缓存的 OpenAI-compatible 客户端（共享缓存是有意行为）。"""
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
    return get_kernel_gemini_client(
        GeminiClientOptions(
            api_key=os.getenv("GEMINI_API_KEY"),
            wrap_langsmith=True,
            tags=("agentic-ai-companion", "gemini"),
            metadata={"source": "experimental"},
            chat_name="AgenticAICompanion_Gemini",
        )
    )


def get_gemini_client():
    """懒加载单例，避免每次工具调用都新建 client。"""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = _create_gemini_client()
    return _gemini_client
