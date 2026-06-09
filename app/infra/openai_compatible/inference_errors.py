"""OpenAI-compatible inference HTTP/API failures mapped to stable client-facing errors."""

from __future__ import annotations

from typing import Any

from loguru import logger


class OpenAICompatibleInferenceBackendError(Exception):
    """LLM provider HTTP/API failure surfaced from the OpenAI-compatible pipeline."""

    def __init__(
        self,
        *,
        client_message_en: str,
        provider_http_status: int | None = None,
    ) -> None:
        super().__init__(client_message_en)
        self.client_message_en = client_message_en
        self.provider_http_status = provider_http_status


_MSG_PROVIDER_GENERIC = "The AI inference request failed at the inference provider. Please try again later."
_MSG_PROVIDER_UNREACHABLE = (
    "Could not reach the AI inference provider. Please try again later."
)
_MSG_PROVIDER_TIMEOUT = (
    "The AI inference provider did not respond in time. Please try again later."
)
_MSG_RATE_LIMIT = "The AI inference provider rate limit was exceeded. Please try again in a moment."
_MSG_BAD_REQUEST = "The AI inference provider rejected the request parameters. Please try again later."
_MSG_AUTH = "The AI inference provider rejected the request due to authentication or permissions."
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


def openai_compatible_inference_backend_error_from_openai(
    exc: Exception,
) -> OpenAICompatibleInferenceBackendError:
    """Build a pipeline-level inference error from an OpenAI SDK exception."""
    from openai import (
        APIConnectionError,
        APIError,
        APIStatusError,
        APITimeoutError,
    )

    if isinstance(exc, APIStatusError):
        code = int(exc.status_code)
        logger.warning(
            "openai_compatible llm inference provider error status={} type={} message={!r} body={!r}",
            code,
            type(exc).__name__,
            getattr(exc, "message", ""),
            getattr(exc, "body", None),
        )
        return OpenAICompatibleInferenceBackendError(
            client_message_en=_client_message_for_provider_status(code),
            provider_http_status=code,
        )
    if isinstance(exc, APITimeoutError):
        logger.warning(
            "openai_compatible llm inference timeout type={} message={!r}",
            type(exc).__name__,
            getattr(exc, "message", ""),
        )
        return OpenAICompatibleInferenceBackendError(
            client_message_en=_MSG_PROVIDER_TIMEOUT,
            provider_http_status=None,
        )
    if isinstance(exc, APIConnectionError):
        logger.warning(
            "openai_compatible llm inference connection error type={} message={!r}",
            type(exc).__name__,
            getattr(exc, "message", ""),
        )
        return OpenAICompatibleInferenceBackendError(
            client_message_en=_MSG_PROVIDER_UNREACHABLE,
            provider_http_status=None,
        )
    if isinstance(exc, APIError):
        logger.warning(
            "openai_compatible llm inference api error type={} message={!r} body={!r}",
            type(exc).__name__,
            getattr(exc, "message", ""),
            getattr(exc, "body", None),
        )
        return OpenAICompatibleInferenceBackendError(
            client_message_en=_MSG_PROVIDER_GENERIC,
            provider_http_status=None,
        )
    logger.warning(
        "openai_compatible llm inference unexpected exc_type={} exc={!r}",
        type(exc).__name__,
        exc,
    )
    return OpenAICompatibleInferenceBackendError(
        client_message_en=_MSG_PROVIDER_GENERIC,
        provider_http_status=None,
    )


def log_and_build_inference_error(
    exc: Exception,
) -> OpenAICompatibleInferenceBackendError:
    """Normalize inference failures into ``OpenAICompatibleInferenceBackendError``."""
    if isinstance(exc, OpenAICompatibleInferenceBackendError):
        return exc
    return openai_compatible_inference_backend_error_from_openai(exc)


def raise_if_chat_completion_missing_choices(resp: Any, *, model: str) -> None:
    """Raise when ``choices`` is missing, null, or an empty list."""
    choices = getattr(resp, "choices", None)
    if isinstance(choices, list) and len(choices) > 0:
        return

    err_raw = getattr(resp, "error", None)
    code: int | None = None
    msg_tail = ""
    if isinstance(err_raw, dict):
        c = err_raw.get("code")
        if isinstance(c, int):
            code = c
        elif isinstance(c, str) and c.strip().isdigit():
            code = int(c.strip())
        msg_tail = str(err_raw.get("message") or "").strip()
    elif err_raw is not None:
        c = getattr(err_raw, "code", None)
        if isinstance(c, int):
            code = c
        msg_tail = str(getattr(err_raw, "message", "") or "").strip()

    logger.warning(
        "openai_compatible chat.completions missing choices model={} raw_error_code={} error_message={!r}",
        model,
        code,
        msg_tail,
    )

    http_status = code if isinstance(code, int) and 100 <= code <= 599 else None
    msg_en = (
        _client_message_for_provider_status(http_status)
        if http_status is not None
        else _MSG_PROVIDER_GENERIC
    )
    raise OpenAICompatibleInferenceBackendError(
        client_message_en=msg_en,
        provider_http_status=http_status,
    )
