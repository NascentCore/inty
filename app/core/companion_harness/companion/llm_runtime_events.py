"""Correlation ContextVar + append path for companion LLM failures in runtime events.

Invoked from :mod:`app.core.companion_harness.llm.chat_completions` on every failed
``chat.completions`` attempt (after normalization) and from :mod:`turn` on structured-chat
foreground timeouts. Production call sites **set** :data:`companion_llm_runtime_event_bind_ctx`
around LLM work (including ``asyncio.to_thread`` and dedicated worker threads); tests may omit
the bind so recording is a no-op.

Do not add unrelated companion imports here—keep this module as the single narrow bridge from
``llm.chat_completions`` into MemoryStore-backed runtime JSONL.
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass
from typing import Any

from loguru import logger

from app.core.companion_harness.companion.llm_inference_errors import (
    CompanionLLMInferenceBackendError,
)
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.companion.runtime_events import (
    append_runtime_event,
)
from app.core.companion_harness.companion.utc import utc_iso_ts

LLM_INFERENCE_FAILURE_KIND = "llm_inference_failure"


@dataclass(frozen=True, slots=True)
class LlmRuntimeEventBind:
    memory_store: MemoryStore
    trace_id: str
    user_msg_uuid: str
    phase: str
    scene: str | None = None


companion_llm_runtime_event_bind_ctx: contextvars.ContextVar[
    LlmRuntimeEventBind | None
] = contextvars.ContextVar("companion_llm_runtime_event_bind_ctx", default=None)


def _is_openrouter_invalid_json_error(exc: BaseException) -> bool:
    """Avoid importing ``OpenRouterInvalidJsonError`` from ``llm.chat_completions`` (cycle-safe)."""
    t = type(exc)
    return t.__name__ == "OpenRouterInvalidJsonError" and t.__module__ in (
        "app.core.companion_harness.llm.chat_completions",
    )


def exc_chain_includes_llm_inference_failure_root_causes(
    exc: BaseException,
) -> bool:
    """True if ``exc`` or ``__cause__`` / ``__context__`` chain carries kernel inference errors."""
    seen: set[int] = set()
    stack: list[BaseException] = [exc]
    while stack:
        cur = stack.pop()
        if id(cur) in seen:
            continue
        seen.add(id(cur))
        if isinstance(cur, CompanionLLMInferenceBackendError):
            return True
        if _is_openrouter_invalid_json_error(cur):
            return True
        cause = cur.__cause__
        ctx = cur.__context__
        if cause is not None:
            stack.append(cause)
        if ctx is not None and ctx is not cause:
            stack.append(ctx)
    return False


def record_llm_inference_failure(
    *,
    model: str,
    exc: BaseException,
    foreground_timeout_sec: float | None = None,
) -> None:
    """Append ``kind=llm_inference_failure`` when bind is set; swallow store errors."""
    bind = companion_llm_runtime_event_bind_ctx.get()
    if bind is None:
        return
    detail = str(exc).strip() or type(exc).__name__
    if len(detail) > 2000:
        detail = detail[:1997] + "..."

    record: dict[str, Any] = {
        "ts": utc_iso_ts(),
        "kind": LLM_INFERENCE_FAILURE_KIND,
        "trace_id": bind.trace_id,
        "user_msg_uuid": bind.user_msg_uuid,
        "phase": bind.phase,
        "model": model,
        "error_type": type(exc).__name__,
        "detail": detail,
    }
    if bind.scene:
        record["scene"] = bind.scene
    if foreground_timeout_sec is not None:
        record["foreground_timeout_sec"] = foreground_timeout_sec
    if isinstance(exc, CompanionLLMInferenceBackendError):
        record["client_message_en"] = exc.client_message_en
        if exc.provider_http_status is not None:
            record["provider_http_status"] = exc.provider_http_status

    try:
        append_runtime_event(bind.memory_store, record)
    except Exception:
        logger.warning(
            "record_llm_inference_failure append failed trace_id={} model={}",
            bind.trace_id,
            model,
            exc_info=True,
        )
