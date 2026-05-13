"""Typed ports for LLM transport in companion_harness (structural typing for tests and DI)."""

from __future__ import annotations

from typing import Any, Protocol


class ChatCompletionsSyncPort(Protocol):
    """Synchronous OpenAI-style ``chat.completions.create`` pipeline (retry, tool kwargs, LangSmith enrich)."""

    def __call__(
        self,
        client: Any,
        *,
        model: str,
        messages_payload: list[dict[str, Any]],
        tools: list[Any],
        tool_choice: str | None = None,
        response_format: dict[str, Any] | None = None,
        langsmith_extra: dict[str, Any] | None = None,
    ) -> Any: ...
