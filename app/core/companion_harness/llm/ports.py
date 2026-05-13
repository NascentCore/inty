"""Structural typing for LLM call boundaries inside companion_harness.

These ``Protocol`` definitions are the *shape* of injectable callables: type checkers
can verify callers and implementations agree without forcing a shared base class or
concrete wrapper type.

``ChatCompletionsSyncPort`` is the sync entry used when code needs one OpenAI-compatible
``chat.completions.create`` round-trip with the harness's agreed kwargs surface (tools,
optional JSON ``response_format``, LangSmith metadata). The canonical implementation is
``create_chat_completion_sync`` in ``llm.chat_completions``; it is exposed from
``CompanionLLMClient.chat_completions_sync`` and injected into background tool paths
(``tools.tool_background``) so foreground and tool loops can share the same pipeline."""

from __future__ import annotations

from typing import Any, Protocol


class ChatCompletionsSyncPort(Protocol):
    """Callable contract for one synchronous chat completion through the harness pipeline.

    Structural type: any ``__call__`` matching the signature below is a valid port.
    Canonical implementation: ``create_chat_completion_sync`` (``llm.chat_completions``);
    wired via ``CompanionLLMClient.chat_completions_sync`` and optional injection in
    ``tools.tool_background``. Return type stays ``Any`` (vendor completion after enrich).
    """

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
