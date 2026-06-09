"""Async OpenAI-compatible chat.completions: high-reasoning kwargs, JSON retry, LangSmith enrich."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from copy import deepcopy
from typing import Any

from loguru import logger

from app.infra.openai_compatible.inference_errors import (
    log_and_build_inference_error,
    raise_if_chat_completion_missing_choices,
)
from app.infra.openai_compatible.langsmith_completion_enrich import (
    _ensure_langsmith_handle_container_end_patch,
    completion_with_langsmith_trace_id,
    reset_wrapped_llm_run_id_for_completion_attempt,
)
from app.infra.openai_compatible.openrouter_tool_params import (
    tool_path_chat_completion_kwargs,
)
from app.utils.models_catalog import resolve_chat_text_model

_OPENROUTER_JSON_MAX_ATTEMPTS = 3
_OPENROUTER_JSON_BACKOFF_SECONDS = (0.25, 0.75)

InferenceFailureRecorder = Callable[[str, BaseException], None]


class OpenRouterInvalidJsonError(RuntimeError):
    """OpenRouter returned a response body that was not valid JSON."""


async def create_chat_completion(
    client: Any,
    *,
    model: str,
    messages_payload: list[dict[str, Any]],
    tools: list[Any],
    tool_choice: str | None = None,
    response_format: dict[str, Any] | None = None,
    langsmith_extra: dict[str, Any] | None = None,
    high_reasoning: bool = False,
    on_inference_failure: InferenceFailureRecorder | None = None,
    provider_kwargs: dict[str, Any] | None = None,
) -> Any:
    _ensure_langsmith_handle_container_end_patch()
    create_kw: dict[str, Any] = {
        "model": model,
        "messages": deepcopy(messages_payload),
    }
    if langsmith_extra:
        create_kw["langsmith_extra"] = langsmith_extra
    if response_format is not None:
        create_kw["response_format"] = response_format
    if high_reasoning:
        create_kw.update(
            tool_path_chat_completion_kwargs(resolve_chat_text_model(model))
        )
    if tools:
        create_kw["tools"] = tools
        create_kw["parallel_tool_calls"] = True
        if tool_choice is not None:
            create_kw["tool_choice"] = tool_choice
    if provider_kwargs:
        for key, value in provider_kwargs.items():
            if key not in create_kw:
                create_kw[key] = value
    for attempt in range(1, _OPENROUTER_JSON_MAX_ATTEMPTS + 1):
        try:
            reset_wrapped_llm_run_id_for_completion_attempt()
            raw = await client.chat.completions.create(**create_kw)
            enriched = completion_with_langsmith_trace_id(raw)
            raise_if_chat_completion_missing_choices(enriched, model=model)
            return enriched
        except json.JSONDecodeError as exc:
            retryable = attempt < _OPENROUTER_JSON_MAX_ATTEMPTS
            logger.warning(
                "openai_compatible.chat_completions invalid_json_response model={} attempt={}/{} retryable={} err={}",
                model,
                attempt,
                _OPENROUTER_JSON_MAX_ATTEMPTS,
                retryable,
                exc,
            )
            if retryable:
                delay = _OPENROUTER_JSON_BACKOFF_SECONDS[min(attempt - 1, 1)]
                await asyncio.sleep(delay)
                continue
            invalid_json_exc = OpenRouterInvalidJsonError(
                "OpenRouter returned a non-JSON response body "
                f"for model={model} after {_OPENROUTER_JSON_MAX_ATTEMPTS} attempts."
            )
            if on_inference_failure is not None:
                on_inference_failure(model, invalid_json_exc)
            raise invalid_json_exc from exc
        except Exception as exc:
            inf = log_and_build_inference_error(exc)
            if on_inference_failure is not None:
                on_inference_failure(model, inf)
            raise inf from exc
