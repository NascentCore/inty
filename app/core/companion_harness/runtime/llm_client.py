"""Companion LLM client: chat completions + plain text completions for curators."""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Literal

from loguru import logger
from pydantic import BaseModel, Field

from app.core.companion_harness.llm.chat_completions import (
    create_chat_completion_sync,
)
from app.core.companion_harness.llm.langsmith_invocation_extra import (
    dreaming_consolidation_langsmith_extra,
)
from app.core.companion_harness.llm.ports import ChatCompletionsSyncPort
from app.core.companion_harness.providers.openai_compatible_clients import (
    OpenAICompatibleClientOptions,
    get_openai_compatible_sync_client,
)
from app.core.companion_harness.runtime.llm_runtime_events import (
    record_llm_inference_failure,
)
from app.utils.models_catalog import DEEPSEEK_V3_2, GenAIModel

LLM_SCENE_CHAT = "chat"
LLM_SCENE_TOOL_CALL = "tool_call"
LLM_SCENE_INNER_TICK = "inner_tick"

LLMScene = Literal["chat", "tool_call", "inner_tick"]


class CompanionLLMConfig(BaseModel):
    """LLM model configuration for companion."""

    default_model: GenAIModel = Field(default_factory=lambda: DEEPSEEK_V3_2)
    chat_model: GenAIModel | None = None
    tool_model: GenAIModel | None = None
    memory_model: GenAIModel | None = None
    day_summary_model: GenAIModel | None = None
    user_model: GenAIModel | None = None
    style_model: GenAIModel | None = None
    soul_model: GenAIModel | None = None
    api_base: str = "https://openrouter.ai/api/v1"
    api_key: str = ""
    async_chat_front_timeout_sec: float = Field(default=600.0, ge=1.0)

    @classmethod
    def from_openrouter_env(cls) -> CompanionLLMConfig:
        """Load credentials and HTTP timeout from the process environment.

        Model identifiers are **not** read from the environment; production and
        scripts should set ``default_model`` / role models via ``config.yaml`` or
        explicit ``CompanionLLMConfig(...)`` construction.
        """
        key = (
            os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
        ).strip()
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
                chat_name="agentic_companion_unified_chat",
            )
        )
        self._client_dual_chat: Any | None = None
        self._client_dual_tool: Any | None = None
        self._client_inner_tick: Any | None = None

    @property
    def config(self) -> CompanionLLMConfig:
        return self._config

    @property
    def chat_completions_sync(self) -> ChatCompletionsSyncPort:
        """Same implementation as foreground ``chat_completion``; inject into tool_background."""
        return create_chat_completion_sync

    def _ensure_dual_chat_client(self) -> Any:
        if self._client_dual_chat is None:
            self._client_dual_chat = get_openai_compatible_sync_client(
                OpenAICompatibleClientOptions(
                    api_key=self._config.api_key or None,
                    base_url=self._config.api_base or None,
                    wrap_langsmith=True,
                    chat_name="agentic_companion_chat",
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
                    chat_name="agentic_companion_tool_call",
                    completions_name="companion_OpenAI",
                    use_fake_openai=False,
                )
            )
        return self._client_dual_tool

    def _ensure_inner_tick_client(self) -> Any:
        if self._client_inner_tick is None:
            self._client_inner_tick = get_openai_compatible_sync_client(
                OpenAICompatibleClientOptions(
                    api_key=self._config.api_key or None,
                    base_url=self._config.api_base or None,
                    wrap_langsmith=True,
                    chat_name="agentic_companion_inner_tick",
                    completions_name="companion_OpenAI",
                    use_fake_openai=False,
                )
            )
        return self._client_inner_tick

    def sync_client_for_route(
        self, route: Literal["unified", "chat", "tool", "inner_tick"]
    ) -> Any:
        if route == "chat":
            return self._ensure_dual_chat_client()
        if route == "tool":
            return self._ensure_dual_tool_client()
        if route == "inner_tick":
            return self._ensure_inner_tick_client()
        return self._client

    def resolve_model(self, role: str) -> GenAIModel:
        """Return catalog model for a config role (``chat``, ``tool``, ``memory``, ...), else ``default_model``."""
        m: GenAIModel | None = getattr(self._config, f"{role}_model", None)
        return m if m is not None else self._config.default_model

    def chat_completion(
        self,
        *,
        messages: list[dict[str, Any]],
        model: GenAIModel | None = None,
        tools: list[Any] | None = None,
        tool_choice: str | None = None,
        response_format: dict[str, Any] | None = None,
        scene: LLMScene | None = None,
        langsmith_extra: dict[str, Any] | None = None,
        high_reasoning: bool = False,
    ) -> Any:
        tool_list = list(tools or [])
        resolved_scene: LLMScene = (
            scene
            if scene is not None
            else (LLM_SCENE_TOOL_CALL if tool_list else LLM_SCENE_CHAT)
        )
        if resolved_scene == LLM_SCENE_INNER_TICK:
            client = self._ensure_inner_tick_client()
            m = model or self.resolve_model("tool" if tool_list else "chat")
        elif resolved_scene == LLM_SCENE_TOOL_CALL:
            client = self._ensure_dual_tool_client()
            m = model or self.resolve_model("tool")
        else:
            client = self._ensure_dual_chat_client()
            m = model or self.resolve_model("chat")
        api_model = m.id_on_provider
        return self.chat_completions_sync(
            client,
            model=api_model,
            messages_payload=messages,
            tools=tool_list,
            tool_choice=tool_choice,
            response_format=response_format,
            langsmith_extra=langsmith_extra,
            high_reasoning=high_reasoning,
        )

    async def chat_completion_with_retrial(
        self,
        *,
        messages: list[dict[str, Any]],
        model: GenAIModel | None,
        tools: list[Any] | None,
        tool_choice: str | None,
        response_format: dict[str, Any] | None,
        scene: LLMScene | None,
        langsmith_extra: dict[str, Any] | None,
        high_reasoning: bool,
        max_attempts: int,
        per_attempt_timeout_sec: float,
        trace_id: str | None,
        attempt_log_label: str,
    ) -> Any:
        resolved = model or self.resolve_model("tool" if tools else "chat")
        model_id = resolved.id_on_provider
        assert max_attempts >= 1
        assert per_attempt_timeout_sec > 0.0
        resp = None
        for attempt in range(1, max_attempts + 1):
            try:
                resp = await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda: self.chat_completion(
                            messages=messages,
                            model=resolved,
                            tools=tools,
                            tool_choice=tool_choice,
                            response_format=response_format,
                            scene=scene,
                            langsmith_extra=langsmith_extra,
                            high_reasoning=high_reasoning,
                        )
                    ),
                    timeout=per_attempt_timeout_sec,
                )
                break
            except asyncio.CancelledError:
                raise
            except BaseException as exc:
                record_llm_inference_failure(
                    model=model_id,
                    exc=exc,
                    foreground_timeout_sec=per_attempt_timeout_sec,
                )
                logger.warning(
                    "chat_completion_with_retrial failed label={} attempt={}/{} "
                    "trace_id={} exc_type={}",
                    attempt_log_label,
                    attempt,
                    max_attempts,
                    trace_id,
                    type(exc).__name__,
                )
                if attempt >= max_attempts:
                    raise
        assert resp is not None
        return resp

    def chat_completion_unified(
        self,
        *,
        messages: list[dict[str, Any]],
        model: GenAIModel | None = None,
        tools: list[Any] | None = None,
        tool_choice: str | None = None,
        high_reasoning: bool = False,
    ) -> Any:
        """Single client path (no dual routing), for bootstrap or tests."""
        m = model or self.resolve_model("tool" if tools else "chat")
        api_model = m.id_on_provider
        return self.chat_completions_sync(
            self._client,
            model=api_model,
            messages_payload=messages,
            tools=list(tools or []),
            tool_choice=tool_choice,
            high_reasoning=high_reasoning,
        )

    def complete_text(
        self,
        messages: list[dict[str, Any]],
        *,
        model_role: str = "memory",
    ) -> str:
        m = self.resolve_model(model_role)
        api_model = m.id_on_provider
        approx_chars = sum(len(str(x.get("content") or "")) for x in messages)
        t_api = time.perf_counter()
        resp = self.chat_completions_sync(
            self._client,
            model=api_model,
            messages_payload=messages,
            tools=[],
            langsmith_extra=dreaming_consolidation_langsmith_extra(
                model_role=model_role
            ),
        )
        api_ms = (time.perf_counter() - t_api) * 1000.0
        logger.info(
            "companion complete_text model_role={} model={} chat_completions_ms={:.0f} approx_chars={}",
            model_role,
            api_model,
            api_ms,
            approx_chars,
        )
        content = resp.choices[0].message.content
        if not isinstance(content, str):
            logger.warning(
                "complete_text got non-string content model_role={} model={}",
                model_role,
                api_model,
            )
            return ""
        return content.strip()
