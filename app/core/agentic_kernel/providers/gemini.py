"""Gemini provider facade with shared client cache."""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Any

from google import genai

from app.utils.google_genai_client import wrap_google_genai_client_with_langsmith


@dataclass(frozen=True)
class GeminiClientOptions:
    api_key: str | None = None
    vertexai: bool = False
    project: str | None = None
    location: str | None = None
    http_options: dict[str, Any] | None = None
    wrap_langsmith: bool = False
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None
    chat_name: str | None = None
    credentials_path: str | None = None


@dataclass(frozen=True)
class _GeminiClientCacheKey:
    api_key: str | None
    vertexai: bool
    project: str | None
    location: str | None
    http_options_items: tuple[Any, ...]
    wrap_langsmith: bool
    tags: tuple[str, ...]
    metadata_items: tuple[Any, ...]
    chat_name: str | None
    credentials_path: str | None


_CLIENT_CACHE_LOCK = threading.Lock()
_CLIENT_CACHE: dict[_GeminiClientCacheKey, Any] = {}


def _to_hashable(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(sorted((str(k), _to_hashable(v)) for k, v in value.items()))
    if isinstance(value, (list, tuple, set)):
        return tuple(_to_hashable(v) for v in value)
    return value


def _build_cache_key(options: GeminiClientOptions) -> _GeminiClientCacheKey:
    return _GeminiClientCacheKey(
        api_key=options.api_key,
        vertexai=options.vertexai,
        project=options.project,
        location=options.location,
        http_options_items=(
            _to_hashable(options.http_options) if options.http_options else ()
        ),
        wrap_langsmith=options.wrap_langsmith,
        tags=tuple(options.tags),
        metadata_items=_to_hashable(options.metadata) if options.metadata else (),
        chat_name=options.chat_name,
        credentials_path=options.credentials_path,
    )


def _build_gemini_client(options: GeminiClientOptions) -> Any:
    kwargs: dict[str, Any] = {}
    if options.api_key:
        kwargs["api_key"] = options.api_key
    if options.vertexai:
        kwargs["vertexai"] = True
    if options.project:
        kwargs["project"] = options.project
    if options.location:
        kwargs["location"] = options.location
    if options.http_options:
        kwargs["http_options"] = options.http_options

    # Do not set GOOGLE_APPLICATION_CREDENTIALS for Vertex: other libraries (TTS, Firebase,
    # or a second inty key path) may overwrite the env, and the genai client would then use
    # the wrong key (JWT invalid_grant / account not found). Pass explicit credentials.
    if options.credentials_path and os.path.exists(options.credentials_path):
        if options.vertexai:
            from google.oauth2 import service_account

            kwargs["credentials"] = service_account.Credentials.from_service_account_file(
                options.credentials_path,
                scopes=("https://www.googleapis.com/auth/cloud-platform",),
            )
        else:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = options.credentials_path

    client = genai.Client(**kwargs)
    if not options.wrap_langsmith:
        return client

    return wrap_google_genai_client_with_langsmith(
        client,
        tags=list(options.tags),
        metadata=options.metadata,
        chat_name=options.chat_name,
    )


def get_gemini_client(options: GeminiClientOptions) -> Any:
    """Get or create cached Gemini client (shared instance by option key)."""
    key = _build_cache_key(options)
    if key in _CLIENT_CACHE:
        return _CLIENT_CACHE[key]
    with _CLIENT_CACHE_LOCK:
        if key in _CLIENT_CACHE:
            return _CLIENT_CACHE[key]
        client = _build_gemini_client(options)
        _CLIENT_CACHE[key] = client
        return client
