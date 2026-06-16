"""Cached OpenAI-compatible sync and async HTTP clients (shared by option key)."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

from app.core.companion_harness.providers.openai_compatible import (
    OpenAICompatibleAsyncOptions,
    OpenAICompatibleSyncOptions,
    create_async_client,
    create_sync_client,
)


@dataclass(frozen=True)
class OpenAICompatibleClientOptions:
    """
    Unified options for constructing OpenAI-compatible clients.

    Shared cache is intentional: clients with identical options return the same instance.
    """

    base_url: str | None
    api_key: str | None
    wrap_langsmith: bool
    chat_name: str | None = None
    completions_name: str | None = None
    timeout: float | None = None
    default_headers: dict[str, str] | None = None
    use_fake_openai: bool = False


@dataclass(frozen=True)
class _OpenAICompatibleClientCacheKey:
    kind: str
    base_url: str | None
    api_key: str | None
    wrap_langsmith: bool
    chat_name: str | None
    completions_name: str | None
    timeout: float | None
    default_headers_items: tuple[tuple[str, str], ...]
    use_fake_openai: bool


_CLIENT_CACHE_LOCK = threading.Lock()
_CLIENT_CACHE: dict[_OpenAICompatibleClientCacheKey, Any] = {}


def _normalized_headers(
    default_headers: dict[str, str] | None,
) -> tuple[tuple[str, str], ...]:
    if not default_headers:
        return ()
    return tuple(sorted(default_headers.items()))


def _build_cache_key(
    kind: str,
    options: OpenAICompatibleClientOptions,
) -> _OpenAICompatibleClientCacheKey:
    return _OpenAICompatibleClientCacheKey(
        kind=kind,
        base_url=options.base_url,
        api_key=options.api_key,
        wrap_langsmith=options.wrap_langsmith,
        chat_name=options.chat_name,
        completions_name=options.completions_name,
        timeout=options.timeout,
        default_headers_items=_normalized_headers(options.default_headers),
        use_fake_openai=options.use_fake_openai,
    )


def _build_openai_compatible_sync_client(
    options: OpenAICompatibleClientOptions,
) -> Any:
    return create_sync_client(
        OpenAICompatibleSyncOptions(
            base_url=options.base_url,
            api_key=options.api_key,
            default_headers=options.default_headers,
            timeout=options.timeout,
            wrap_langsmith=options.wrap_langsmith,
            chat_name=options.chat_name,
            completions_name=options.completions_name,
            use_fake_openai=options.use_fake_openai,
        )
    )


def _build_openai_compatible_async_client(
    options: OpenAICompatibleClientOptions,
) -> Any:
    return create_async_client(
        OpenAICompatibleAsyncOptions(
            base_url=options.base_url,
            api_key=options.api_key,
            default_headers=options.default_headers,
            timeout=options.timeout,
            wrap_langsmith=options.wrap_langsmith,
            chat_name=options.chat_name,
            completions_name=options.completions_name,
            use_fake_openai=options.use_fake_openai,
        )
    )


def get_openai_compatible_sync_client(
    options: OpenAICompatibleClientOptions,
) -> Any:
    """Get or create cached OpenAI-compatible sync client (shared instance by option key)."""
    key = _build_cache_key("sync", options)
    if key in _CLIENT_CACHE:
        return _CLIENT_CACHE[key]
    with _CLIENT_CACHE_LOCK:
        if key in _CLIENT_CACHE:
            return _CLIENT_CACHE[key]
        client = _build_openai_compatible_sync_client(options=options)
        _CLIENT_CACHE[key] = client
        return client


def get_openai_compatible_async_client(
    options: OpenAICompatibleClientOptions,
) -> Any:
    """Get or create cached OpenAI-compatible async client (shared instance by option key)."""
    key = _build_cache_key("async", options)
    if key in _CLIENT_CACHE:
        return _CLIENT_CACHE[key]
    with _CLIENT_CACHE_LOCK:
        if key in _CLIENT_CACHE:
            return _CLIENT_CACHE[key]
        client = _build_openai_compatible_async_client(options=options)
        _CLIENT_CACHE[key] = client
        return client
