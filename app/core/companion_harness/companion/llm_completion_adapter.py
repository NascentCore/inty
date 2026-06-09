"""Companion-bound chat completion: infra async pipeline + runtime failure recording."""

from __future__ import annotations

from typing import Any

from app.core.companion_harness.companion.llm_runtime_events import (
    record_llm_inference_failure,
)
from app.infra.openai_compatible.chat_completions import (
    create_chat_completion as _infra_create_chat_completion,
)


async def create_chat_completion(client: Any, **kwargs: Any) -> Any:
    return await _infra_create_chat_completion(
        client,
        on_inference_failure=lambda model, exc: record_llm_inference_failure(
            model=model,
            exc=exc,
        ),
        **kwargs,
    )
