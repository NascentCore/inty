"""Model client abstractions for framework stage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openai import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)


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


@dataclass(frozen=True)
class ModelAvailabilityResult:
    model_id: str
    status: str
    is_available: bool
    detail: str


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


class OpenRouterModelAvailabilityProbe:
    """Probe model availability through OpenRouter-compatible endpoint."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str | None,
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key

    def probe(
        self,
        *,
        model_id: str,
        timeout_seconds: float,
        dry_run: bool,
    ) -> ModelAvailabilityResult:
        if dry_run:
            return ModelAvailabilityResult(
                model_id=model_id,
                status="skipped",
                is_available=False,
                detail="dry_run enabled",
            )
        if not self._api_key:
            return ModelAvailabilityResult(
                model_id=model_id,
                status="skipped",
                is_available=False,
                detail="OPENROUTER_API_KEY / OPENAI_API_KEY is not configured",
            )

        client = OpenAI(
            base_url=self._base_url,
            api_key=self._api_key,
        )
        try:
            completion = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": "Reply with OK only."}],
                max_tokens=8,
                temperature=0.0,
                timeout=timeout_seconds,
            )
            finish_reason = (
                completion.choices[0].finish_reason if completion.choices else "unknown"
            )
            return ModelAvailabilityResult(
                model_id=model_id,
                status="available",
                is_available=True,
                detail=f"finish_reason={finish_reason}",
            )
        except NotFoundError as exc:
            return ModelAvailabilityResult(
                model_id=model_id,
                status="unavailable",
                is_available=False,
                detail=str(exc),
            )
        except (AuthenticationError, PermissionDeniedError) as exc:
            return ModelAvailabilityResult(
                model_id=model_id,
                status="auth_error",
                is_available=False,
                detail=str(exc),
            )
        except (RateLimitError, BadRequestError, APIConnectionError, APIError) as exc:
            return ModelAvailabilityResult(
                model_id=model_id,
                status="error",
                is_available=False,
                detail=str(exc),
            )


class OpenRouterModelClient:
    """OpenRouter-compatible chat model client for real experiment execution."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
    ) -> None:
        self._client = OpenAI(
            base_url=base_url,
            api_key=api_key,
        )

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
        try:
            completion = self._client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                timeout=timeout_seconds,
            )
        except NotFoundError as exc:
            return ModelInvocationResult(
                output_text=None,
                finish_reason=None,
                status="error",
                error_message=str(exc),
                metadata={"error_type": "not_found"},
            )
        except (AuthenticationError, PermissionDeniedError) as exc:
            return ModelInvocationResult(
                output_text=None,
                finish_reason=None,
                status="error",
                error_message=str(exc),
                metadata={"error_type": "auth"},
            )
        except RateLimitError as exc:
            return ModelInvocationResult(
                output_text=None,
                finish_reason=None,
                status="error",
                error_message=str(exc),
                metadata={"error_type": "rate_limit"},
            )
        except (BadRequestError, APIConnectionError, APIError) as exc:
            return ModelInvocationResult(
                output_text=None,
                finish_reason=None,
                status="error",
                error_message=str(exc),
                metadata={"error_type": "api"},
            )

        if not completion.choices:
            return ModelInvocationResult(
                output_text=None,
                finish_reason=None,
                status="error",
                error_message="No completion choices returned",
                metadata={"error_type": "empty_choices"},
            )

        choice = completion.choices[0]
        finish_reason = choice.finish_reason
        message = choice.message
        output_text = message.content or ""
        refusal_reason = getattr(message, "refusal", None)
        usage = completion.usage
        metadata = {
            "finish_reason": finish_reason,
            "usage": (
                {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                }
                if usage
                else {}
            ),
        }

        if finish_reason == "content_filter" or (
            refusal_reason and not output_text.strip()
        ):
            return ModelInvocationResult(
                output_text=output_text,
                finish_reason=finish_reason,
                status="refusal",
                refusal_reason=refusal_reason or finish_reason,
                metadata=metadata,
            )

        if output_text.strip():
            return ModelInvocationResult(
                output_text=output_text,
                finish_reason=finish_reason,
                status="success",
                metadata=metadata,
            )

        return ModelInvocationResult(
            output_text=output_text,
            finish_reason=finish_reason,
            status="error",
            error_message="Empty completion text",
            metadata=metadata | {"error_type": "empty_text"},
        )
