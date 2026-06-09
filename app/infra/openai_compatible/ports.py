"""Structural typing for injectable OpenAI-compatible chat completion callables."""

from __future__ import annotations

from typing import Any, Protocol


class ChatCompletionsPort(Protocol):
    """Callable contract for one async chat completion through the shared pipeline."""

    async def __call__(
        self,
        client: Any,
        *,
        model: str,
        messages_payload: list[dict[str, Any]],
        tools: list[Any],
        tool_choice: str | None = None,
        response_format: dict[str, Any] | None = None,
        langsmith_extra: dict[str, Any] | None = None,
        high_reasoning: bool = False,
        provider_kwargs: dict[str, Any] | None = None,
    ) -> Any: ...
