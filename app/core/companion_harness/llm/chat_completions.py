"""Synchronous OpenAI-compatible chat.completions: optional high-reasoning kwargs, JSON retry, LangSmith enrich.

Maps OpenAI SDK failures from ``chat.completions.create`` to companion kernel inference errors.
Also rejects responses with missing or empty ``choices`` (including OpenRouter HTTP 200 bodies
with ``choices: null``, optionally plus ``error``), mapping them to kernel inference errors
instead of crashing on ``choices[0]``.
"""

from __future__ import annotations

import json
import time
from copy import deepcopy
from typing import Any

from loguru import logger

from app.core.companion_harness.companion.llm_inference_errors import (
    log_and_build_inference_error,
    raise_if_chat_completion_missing_choices,
)
from app.core.companion_harness.companion.llm_runtime_events import (
    record_llm_inference_failure,
)
from app.core.companion_harness.llm.langsmith_completion_enrich import (
    _ensure_langsmith_handle_container_end_patch,
    completion_with_langsmith_trace_id,
    reset_wrapped_llm_run_id_for_completion_attempt,
)
from app.core.companion_harness.llm.openrouter_tool_params import (
    tool_path_chat_completion_kwargs,
)
from app.utils.models_catalog import resolve_chat_text_model

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
    langsmith_extra: dict[str, Any] | None = None,
    high_reasoning: bool = False,
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
    # Some gateways place structured ``response_format`` JSON under ``reasoning`` /
    # ``reasoning_details`` while leaving ``message.content`` empty. Companion parsing validates
    # those side channels before using them; raw non-JSON reasoning is never surfaced.
    if high_reasoning:
        create_kw.update(
            tool_path_chat_completion_kwargs(resolve_chat_text_model(model))
        )
    if tools:
        create_kw["tools"] = tools
        create_kw["parallel_tool_calls"] = True
        if tool_choice is not None:
            create_kw["tool_choice"] = tool_choice
    for attempt in range(1, _OPENROUTER_JSON_MAX_ATTEMPTS + 1):
        try:
            reset_wrapped_llm_run_id_for_completion_attempt()
            raw = client.chat.completions.create(**create_kw)
            enriched = completion_with_langsmith_trace_id(raw)
            raise_if_chat_completion_missing_choices(enriched, model=model)
            return enriched
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
            invalid_json_exc = OpenRouterInvalidJsonError(
                "OpenRouter returned a non-JSON response body "
                f"for model={model} after {_OPENROUTER_JSON_MAX_ATTEMPTS} attempts."
            )
            record_llm_inference_failure(model=model, exc=invalid_json_exc)
            raise invalid_json_exc from exc
        except Exception as exc:
            inf = log_and_build_inference_error(exc)
            record_llm_inference_failure(model=model, exc=inf)
            raise inf from exc
