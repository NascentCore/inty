"""Companion LLM client: chat completions + plain text completions for curators."""

from __future__ import annotations

import os
import time
from typing import Any, Literal

from loguru import logger
from pydantic import BaseModel, Field

from app.core.agentic_kernel.providers.facade import (
    OpenAICompatibleClientOptions,
    get_openai_compatible_sync_client,
)

from .llm_chat_runtime import create_chat_completion_sync


def async_tool_background_enabled_from_env() -> bool:
    raw = os.environ.get("INTY_V2_PROTO_ASYNC_TOOL_BG")
    if raw is None or not str(raw).strip():
        return True
    s = str(raw).strip().lower()
    if s in ("0", "false", "no", "off"):
        return False
    if s in ("1", "true", "yes", "on"):
        return True
    raise ValueError(
        f"Invalid INTY_V2_PROTO_ASYNC_TOOL_BG={raw!r}; use 1/true or 0/false, or unset for default (on)"
    )


class CompanionLLMConfig(BaseModel):
    """LLM model configuration for companion."""

    default_model: str = "deepseek/deepseek-v3.2"
    chat_model: str = ""
    tool_model: str = ""
    memory_model: str = ""
    day_summary_model: str = ""
    user_model: str = ""
    soul_model: str = ""
    api_base: str = "https://openrouter.ai/api/v1"
    api_key: str = ""
    enable_async_tool_background: bool = False
    async_chat_front_timeout_sec: float = Field(default=600.0, ge=1.0)

    @classmethod
    def from_openrouter_env(
        cls,
        *,
        default_async_tool_background: bool | None = None,
    ) -> CompanionLLMConfig:
        key = (
            os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
        ).strip()
        async_bg = (
            async_tool_background_enabled_from_env()
            if default_async_tool_background is None
            else default_async_tool_background
        )
        timeout_raw = os.getenv(
            "INTY_V2_PROTO_ASYNC_CHAT_FRONT_TIMEOUT_SEC", "600"
        ).strip()
        try:
            timeout_sec = float(timeout_raw) if timeout_raw else 600.0
        except ValueError:
            timeout_sec = 600.0
        return cls(
            api_key=key,
            api_base=os.getenv(
                "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
            ).strip()
            or "https://openrouter.ai/api/v1",
            default_model=os.getenv(
                "INTY_V2_PROTO_MODEL", "deepseek/deepseek-v3.2"
            ).strip()
            or "deepseek/deepseek-v3.2",
            chat_model=(os.getenv("INTY_V2_PROTO_CHAT_MODEL") or "").strip(),
            tool_model=(os.getenv("INTY_V2_PROTO_TOOL_MODEL") or "").strip(),
            memory_model=(os.getenv("INTY_V2_PROTO_MEMORY_MODEL") or "").strip(),
            day_summary_model=(
                os.getenv("INTY_V2_PROTO_DAY_SUMMARY_MODEL") or ""
            ).strip(),
            user_model=(os.getenv("INTY_V2_PROTO_USER_MODEL") or "").strip(),
            soul_model=(os.getenv("INTY_V2_PROTO_SOUL_MODEL") or "").strip(),
            enable_async_tool_background=async_bg,
            async_chat_front_timeout_sec=timeout_sec,
        )


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
        self._client_dual_chat: Any | None = None
        self._client_dual_tool: Any | None = None

    @property
    def config(self) -> CompanionLLMConfig:
        return self._config

    def _ensure_dual_chat_client(self) -> Any:
        if self._client_dual_chat is None:
            self._client_dual_chat = get_openai_compatible_sync_client(
                OpenAICompatibleClientOptions(
                    api_key=self._config.api_key or None,
                    base_url=self._config.api_base or None,
                    wrap_langsmith=True,
                    chat_name="companion_dual_chat",
                    completions_name="companion_OpenAI",
                    use_fake_openai=False,
                )
            )
        return self._client_dual_chat

    def _ensure_dual_tool_client(self) -> Any:
        if self._client_dual_tool is None:
            self._client_dual_tool = get_openai_compatible_sync_client(
                OpenAICompatibleClientOptions(
                    api_key=self._config.api_key or None,
                    base_url=self._config.api_base or None,
                    wrap_langsmith=True,
                    chat_name="companion_dual_tool",
                    completions_name="companion_OpenAI",
                    use_fake_openai=False,
                )
            )
        return self._client_dual_tool

    def sync_client_for_route(self, route: Literal["unified", "chat", "tool"]) -> Any:
        if route == "chat":
            return self._ensure_dual_chat_client()
        if route == "tool":
            return self._ensure_dual_tool_client()
        return self._client

    def _resolve_model(self, role: str) -> str:
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
        tool_list = list(tools or [])
        has_tools = bool(tool_list)
        if has_tools:
            client = self._ensure_dual_tool_client()
            m = model or self._resolve_model("tool")
        else:
            client = self._ensure_dual_chat_client()
            m = model or self._resolve_model("chat")
        return create_chat_completion_sync(
            client,
            model=m,
            messages_payload=messages,
            tools=tool_list,
            tool_choice=tool_choice,
        )

    def chat_completion_unified(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str | None = None,
        tools: list[Any] | None = None,
        tool_choice: str | None = None,
    ) -> Any:
        """Single client path (no dual routing), for bootstrap or tests."""
        m = model or self._resolve_model("tool" if tools else "chat")
        return create_chat_completion_sync(
            self._client,
            model=m,
            messages_payload=messages,
            tools=list(tools or []),
            tool_choice=tool_choice,
        )

    def complete_text(
        self,
        messages: list[dict[str, Any]],
        *,
        model_role: str = "memory",
    ) -> str:
        m = self._resolve_model(model_role)
        approx_chars = sum(len(str(x.get("content") or "")) for x in messages)
        t_api = time.perf_counter()
        resp = self._client.chat.completions.create(model=m, messages=messages)
        api_ms = (time.perf_counter() - t_api) * 1000.0
        logger.info(
            "companion complete_text model_role={} model={} chat_completions_ms={:.0f} approx_chars={}",
            model_role,
            m,
            api_ms,
            approx_chars,
        )
        content = resp.choices[0].message.content
        if not isinstance(content, str):
            logger.warning(
                "complete_text got non-string content model_role={} model={}",
                model_role,
                m,
            )
            return ""
        return content.strip()
