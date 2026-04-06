"""Companion LLM client: chat completions + plain text completions for curators."""

from __future__ import annotations

from typing import Any

from loguru import logger
from pydantic import BaseModel

from app.core.agentic_kernel.providers.facade import (
    OpenAICompatibleClientOptions,
    get_openai_compatible_sync_client,
)


class CompanionLLMConfig(BaseModel):
    """LLM model configuration for companion."""

    default_model: str = "deepseek/deepseek-v3.2"
    chat_model: str = ""  # if empty, uses default_model
    tool_model: str = ""  # if empty, uses default_model
    memory_model: str = ""  # if empty, uses default_model
    day_summary_model: str = ""  # if empty, uses default_model
    user_model: str = ""  # if empty, uses default_model
    soul_model: str = ""  # if empty, uses default_model
    api_base: str = "https://openrouter.ai/api/v1"
    api_key: str = ""


class CompanionLLMClient:
    """Manages OpenAI-compatible clients for companion interactions."""

    def __init__(self, config: CompanionLLMConfig) -> None:
        self._config = config
        self._client = get_openai_compatible_sync_client(
            OpenAICompatibleClientOptions(
                api_key=config.api_key or None,
                base_url=config.api_base or None,
                wrap_langsmith=True,
                chat_name="companion",
            )
        )

    def _resolve_model(self, role: str) -> str:
        """Resolve model name for a given role, falling back to default."""
        model = getattr(self._config, f"{role}_model", "") or ""
        return model if model else self._config.default_model

    def chat_completion(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str | None = None,
        tools: list[Any] | None = None,
        tool_choice: str | None = None,
    ) -> Any:
        """Call chat.completions.create."""
        m = model or self._resolve_model("chat")
        kwargs: dict[str, Any] = {"model": m, "messages": messages}
        if tools:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        return self._client.chat.completions.create(**kwargs)

    def complete_text(
        self,
        messages: list[dict[str, Any]],
        *,
        model_role: str = "memory",
    ) -> str:
        """Plain text completion for memory curators etc. Returns assistant content."""
        m = self._resolve_model(model_role)
        resp = self._client.chat.completions.create(model=m, messages=messages)
        content = resp.choices[0].message.content
        if not isinstance(content, str):
            logger.warning(
                "complete_text got non-string content model_role={} model={}",
                model_role,
                m,
            )
            return ""
        return content.strip()
