"""OpenRouter-specific kwargs merged into chat.completions when tools are enabled."""

from __future__ import annotations

import os
from typing import Any

from app.utils.models_catalog import (
    GenAIModel,
    is_deepseek_on_openrouter,
    is_gemini_model,
)


def tool_path_chat_completion_kwargs(model: GenAIModel) -> dict[str, Any]:
    raw = os.environ.get("INTY_V2_PROTO_TOOL_THINKING")
    if raw is not None and str(raw).strip().lower() in (
        "0",
        "false",
        "no",
        "off",
        "none",
    ):
        return {}

    if is_deepseek_on_openrouter(model):
        return {"extra_body": {"reasoning": {"effort": "high", "exclude": True}}}
    if is_gemini_model(model):
        return {"reasoning_effort": "high"}
    return {}
