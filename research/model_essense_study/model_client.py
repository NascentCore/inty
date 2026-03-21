"""Model client abstraction for framework stage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelInvocationRequest:
    model_id: str
    messages: list[dict[str, str]]
    temperature: float
    max_tokens: int
    top_p: float
    timeout_seconds: float


@dataclass(frozen=True)
class ModelInvocationResult:
    output_text: str | None
    finish_reason: str | None
    status: str
    error_message: str | None = None
    refusal_reason: str | None = None
    metadata: dict[str, Any] | None = None


class UnsupportedModelClient:
    """
    Framework-stage client: no real API calls yet.
    """

    def generate(
        self,
        *,
        model_id: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        top_p: float,
        timeout_seconds: float,
    ) -> ModelInvocationResult:
        _ = (
            model_id,
            messages,
            temperature,
            max_tokens,
            top_p,
            timeout_seconds,
        )
        return ModelInvocationResult(
            output_text=None,
            finish_reason=None,
            status="error",
            error_message="Model invocation is not implemented in framework-only stage.",
            refusal_reason=None,
            metadata={"stage": "framework_scaffold"},
        )
