"""Companion kernel errors when the OpenAI-compatible inference HTTP API fails.

Maps SDK exceptions from chat.completions into ``CompanionLLMInferenceBackendError``
so API/WebSocket layers can return stable English messages plus optional provider HTTP status.
Also rejects chat completion responses with missing or empty ``choices`` (invalid for normal
consumption): converts them to ``CompanionLLMInferenceBackendError`` instead of letting
downstream crash on ``resp.choices[0]``. When an ``error`` body is present (OpenRouter may
return HTTP 200 with ``choices: null`` and upstream status in ``error.code``), that status
maps to the client message; otherwise ``provider_http_status`` is ``None`` and a generic
provider message is used.
"""

from __future__ import annotations

from typing import Any

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


def companion_llm_inference_backend_error_from_openai(
    exc: Exception,
) -> CompanionLLMInferenceBackendError:
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


def log_and_build_inference_error(
    exc: Exception,
) -> CompanionLLMInferenceBackendError:
    """Normalize inference failures into ``CompanionLLMInferenceBackendError``."""
    if isinstance(exc, CompanionLLMInferenceBackendError):
        return exc
    return companion_llm_inference_backend_error_from_openai(exc)


def raise_if_chat_completion_missing_choices(resp: Any, *, model: str) -> None:
    """Raise when ``choices`` is missing, null, or an empty list.

    Normal chat completions must expose at least one choice; otherwise callers cannot read
    ``resp.choices[0]`` without ``TypeError`` / ``IndexError``. Map every such response to
    ``CompanionLLMInferenceBackendError`` so HTTP/WS layers return ``code 502`` with
    ``error_kind=llm_inference_backend``.

    Typical trigger (observed on OpenRouter): HTTP 200 with
    ``{"choices": null, "error": {"code": <upstream_http_status>, "message": "..."}}`` when
    the upstream provider failed; ``error.code`` becomes ``provider_http_status`` when it is a
    valid HTTP status. If there is no usable ``error`` payload, ``provider_http_status`` is
    ``None`` and the client message is the generic inference-provider failure string.
    """
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
        "companion chat.completions missing choices model={} raw_error_code={} error_message={!r}",
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
    raise CompanionLLMInferenceBackendError(
        client_message_en=msg_en,
        provider_http_status=http_status,
    )
