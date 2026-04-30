"""OpenRouter chat.completions helpers: tool-path kwargs and JSON retry."""

from __future__ import annotations

import json
import time
from copy import deepcopy
from typing import Any

from loguru import logger

_OPENROUTER_JSON_MAX_ATTEMPTS = 3
_OPENROUTER_JSON_BACKOFF_SECONDS = (0.25, 0.75)


class OpenRouterInvalidJsonError(RuntimeError):
    """OpenRouter returned a response body that was not valid JSON."""


def langsmith_trace_id_from_completion(resp: Any) -> str:
    """Reads optional ``langsmith_trace_id`` copied onto the ChatCompletion by ``create_chat_completion_sync``."""
    try:
        v = getattr(resp, "langsmith_trace_id", None)
        if v is None:
            return ""
        return str(v).strip()
    except Exception:
        return ""


def _attach_langsmith_trace_to_completion(resp: Any) -> Any:
    """Best-effort: LangSmith RunTree ``trace_id`` (root trace UUID) onto the completion object."""
    try:
        if langsmith_trace_id_from_completion(resp):
            return resp
        from langsmith.run_helpers import get_current_run_tree

        rt = get_current_run_tree()
        if rt is None:
            return resp
        tid = getattr(rt, "trace_id", None)
        if tid is None:
            return resp
        s = str(tid).strip()
        if not s:
            return resp
        model_copy = getattr(resp, "model_copy", None)
        if model_copy is None:
            return resp
        return model_copy(update={"langsmith_trace_id": s})
    except Exception:
        return resp


def tool_path_chat_completion_kwargs(model: str) -> dict[str, Any]:
    import os

    raw = os.environ.get("INTY_V2_PROTO_TOOL_THINKING")
    if raw is not None and str(raw).strip().lower() in (
        "0",
        "false",
        "no",
        "off",
        "none",
    ):
        return {}

    from app.utils.models_catalog import is_deepseek_on_openrouter, is_gemini_model

    if is_deepseek_on_openrouter(model):
        return {"extra_body": {"reasoning": {"effort": "high", "exclude": True}}}
    if is_gemini_model(model):
        return {"reasoning_effort": "high"}
    return {}


def create_chat_completion_sync(
    client: Any,
    *,
    model: str,
    messages_payload: list[dict[str, Any]],
    tools: list[Any],
    tool_choice: str | None = None,
    response_format: dict[str, Any] | None = None,
) -> Any:
    create_kw: dict[str, Any] = {
        "model": model,
        "messages": deepcopy(messages_payload),
    }
    if response_format is not None:
        create_kw["response_format"] = response_format
    if tools:
        create_kw.update(tool_path_chat_completion_kwargs(model))
        create_kw["tools"] = tools
        create_kw["parallel_tool_calls"] = True
        if tool_choice is not None:
            create_kw["tool_choice"] = tool_choice
    for attempt in range(1, _OPENROUTER_JSON_MAX_ATTEMPTS + 1):
        try:
            raw = client.chat.completions.create(**create_kw)
            return _attach_langsmith_trace_to_completion(raw)
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
