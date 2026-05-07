"""Synchronous OpenAI-compatible chat.completions: tool-path kwargs, JSON retry, LangSmith enrich.

Maps OpenAI SDK failures from ``chat.completions.create`` to companion kernel inference errors.
"""

from __future__ import annotations

import json
import time
from copy import deepcopy
from typing import Any

from loguru import logger

from app.core.agentic_kernel.companion.llm_inference_errors import (
    log_and_build_inference_error,
)
from app.core.agentic_kernel.llm.langsmith_completion_enrich import (
    _ensure_langsmith_handle_container_end_patch,
    completion_with_langsmith_trace_id,
    reset_wrapped_llm_run_id_for_completion_attempt,
)
from app.core.agentic_kernel.llm.openrouter_tool_params import (
    tool_path_chat_completion_kwargs,
)

_OPENROUTER_JSON_MAX_ATTEMPTS = 3
_OPENROUTER_JSON_BACKOFF_SECONDS = (0.25, 0.75)


class OpenRouterInvalidJsonError(RuntimeError):
    """OpenRouter returned a response body that was not valid JSON."""


def create_chat_completion_sync(
    client: Any,
    *,
    model: str,
    messages_payload: list[dict[str, Any]],
    tools: list[Any],
    tool_choice: str | None = None,
    response_format: dict[str, Any] | None = None,
) -> Any:
    _ensure_langsmith_handle_container_end_patch()
    create_kw: dict[str, Any] = {
        "model": model,
        "messages": deepcopy(messages_payload),
    }
    if response_format is not None:
        create_kw["response_format"] = response_format
    # TODO(companion-dual-envelope-reasoning-channel): Switching chat models (e.g. OpenRouter
    # DeepSeek) can surface HTTP 500 ``Chat returned no content`` while LangSmith still shows text:
    # ``choices[0].message.content`` is null but ``reasoning`` / ``reasoning_details`` holds the
    # visible reply or JSON envelope. Observed with ``deepseek/deepseek-v4-pro``; ``deepseek-v3.2``
    # often returned proper ``content``. Mitigation: when ``response_format`` is set and ``tools``
    # is empty, still ``create_kw.update(tool_path_chat_completion_kwargs(model))`` so structured
    # chat gets the same DeepSeek ``reasoning.exclude`` profile as the tool path; optionally parse
    # fallback text from ``reasoning`` in ``turn.py`` / ``tool_background.py``.
    if tools:
        create_kw.update(tool_path_chat_completion_kwargs(model))
        create_kw["tools"] = tools
        create_kw["parallel_tool_calls"] = True
        if tool_choice is not None:
            create_kw["tool_choice"] = tool_choice
    for attempt in range(1, _OPENROUTER_JSON_MAX_ATTEMPTS + 1):
        try:
            reset_wrapped_llm_run_id_for_completion_attempt()
            raw = client.chat.completions.create(**create_kw)
            return completion_with_langsmith_trace_id(raw)
        except json.JSONDecodeError as exc:
            retryable = attempt < _OPENROUTER_JSON_MAX_ATTEMPTS
            logger.warning(
                "llm.chat_completions invalid_json_response model={} attempt={}/{} retryable={} err={}",
                model,
                attempt,
                _OPENROUTER_JSON_MAX_ATTEMPTS,
                retryable,
                exc,
            )
            if retryable:
                delay = _OPENROUTER_JSON_BACKOFF_SECONDS[min(attempt - 1, 1)]
                time.sleep(delay)
                continue
            raise OpenRouterInvalidJsonError(
                "OpenRouter returned a non-JSON response body "
                f"for model={model} after {_OPENROUTER_JSON_MAX_ATTEMPTS} attempts."
            ) from exc
        except Exception as exc:
            raise log_and_build_inference_error(exc) from exc
