"""Companion kernel errors when the OpenAI-compatible inference HTTP API fails.

Maps SDK exceptions from chat.completions into ``CompanionLLMInferenceBackendError``
so API/WebSocket layers can return stable English messages plus optional provider HTTP status.
"""

from __future__ import annotations

from loguru import logger


class CompanionLLMInferenceBackendError(Exception):
    """LLM provider HTTP/API failure surfaced from the companion kernel."""

    def __init__(
        self,
        *,
        client_message_en: str,
        provider_http_status: int | None = None,
    ) -> None:
        super().__init__(client_message_en)
        self.client_message_en = client_message_en
        self.provider_http_status = provider_http_status


_MSG_PROVIDER_GENERIC = (
    "The AI inference request failed at the inference provider. Please try again later."
)
_MSG_PROVIDER_UNREACHABLE = (
    "Could not reach the AI inference provider. Please try again later."
)
_MSG_PROVIDER_TIMEOUT = (
    "The AI inference provider did not respond in time. Please try again later."
)
_MSG_RATE_LIMIT = (
    "The AI inference provider rate limit was exceeded. Please try again in a moment."
)
_MSG_BAD_REQUEST = (
    "The AI inference provider rejected the request parameters. Please try again later."
)
_MSG_AUTH = (
    "The AI inference provider rejected the request due to authentication or permissions."
)
_MSG_PAYMENT_OR_QUOTA = (
    "The AI inference provider rejected this request due to insufficient credits, quota, "
    "or token limits on the service side. Please try again later."
)
_MSG_PROVIDER_5XX = (
    "The AI inference provider returned an error. Please try again later."
)


def _client_message_for_provider_status(status_code: int) -> str:
    if status_code == 401 or status_code == 403:
        return _MSG_AUTH
    if status_code == 402:
        return _MSG_PAYMENT_OR_QUOTA
    if status_code == 429:
        return _MSG_RATE_LIMIT
    if status_code == 400 or status_code == 422:
        return _MSG_BAD_REQUEST
    if status_code == 408:
        return _MSG_PROVIDER_TIMEOUT
    if status_code >= 500:
        return _MSG_PROVIDER_5XX
    return _MSG_PROVIDER_GENERIC


def companion_llm_inference_backend_error_from_openai(exc: Exception) -> CompanionLLMInferenceBackendError:
    """Build a kernel-level inference error from an OpenAI SDK exception."""
    from openai import (
        APIConnectionError,
        APIError,
        APIStatusError,
        APITimeoutError,
    )

    if isinstance(exc, APIStatusError):
        code = int(exc.status_code)
        logger.warning(
            "companion llm inference provider error status={} type={} message={!r} body={!r}",
            code,
            type(exc).__name__,
            getattr(exc, "message", ""),
            getattr(exc, "body", None),
        )
        return CompanionLLMInferenceBackendError(
            client_message_en=_client_message_for_provider_status(code),
            provider_http_status=code,
        )
    if isinstance(exc, APITimeoutError):
        logger.warning(
            "companion llm inference timeout type={} message={!r}",
            type(exc).__name__,
            getattr(exc, "message", ""),
        )
        return CompanionLLMInferenceBackendError(
            client_message_en=_MSG_PROVIDER_TIMEOUT,
            provider_http_status=None,
        )
    if isinstance(exc, APIConnectionError):
        logger.warning(
            "companion llm inference connection error type={} message={!r}",
            type(exc).__name__,
            getattr(exc, "message", ""),
        )
        return CompanionLLMInferenceBackendError(
            client_message_en=_MSG_PROVIDER_UNREACHABLE,
            provider_http_status=None,
        )
    if isinstance(exc, APIError):
        logger.warning(
            "companion llm inference api error type={} message={!r} body={!r}",
            type(exc).__name__,
            getattr(exc, "message", ""),
            getattr(exc, "body", None),
        )
        return CompanionLLMInferenceBackendError(
            client_message_en=_MSG_PROVIDER_GENERIC,
            provider_http_status=None,
        )
    logger.warning(
        "companion llm inference unexpected exc_type={} exc={!r}",
        type(exc).__name__,
        exc,
    )
    return CompanionLLMInferenceBackendError(
        client_message_en=_MSG_PROVIDER_GENERIC,
        provider_http_status=None,
    )


def log_and_build_inference_error(exc: Exception) -> CompanionLLMInferenceBackendError:
    """Normalize inference failures into ``CompanionLLMInferenceBackendError``."""
    if isinstance(exc, CompanionLLMInferenceBackendError):
        return exc
    return companion_llm_inference_backend_error_from_openai(exc)
