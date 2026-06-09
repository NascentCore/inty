"""OpenAI-compatible provider client construction primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langsmith import wrappers
from openai import AsyncOpenAI, OpenAI

from app.external_services.fakes.openai import FakeOpenAI
from app.infra.openai_compatible.langsmith_completion_enrich import (
    _ensure_langsmith_handle_container_end_patch,
)


@dataclass(frozen=True)
class OpenAICompatibleSyncOptions:
    base_url: str | None
    api_key: str | None
    default_headers: dict[str, str] | None = None
    timeout: float | None = None
    wrap_langsmith: bool = False
    chat_name: str | None = None
    completions_name: str | None = None
    use_fake_openai: bool = False


@dataclass(frozen=True)
class OpenAICompatibleAsyncOptions:
    base_url: str | None
    api_key: str | None
    default_headers: dict[str, str] | None = None
    timeout: float | None = None
    wrap_langsmith: bool = False
    chat_name: str | None = None
    completions_name: str | None = None
    use_fake_openai: bool = False


def _wrap_openai_client(
    base_client: Any,
    *,
    chat_name: str | None,
    completions_name: str | None,
) -> Any:
    _ensure_langsmith_handle_container_end_patch()
    return wrappers.wrap_openai(
        base_client,
        chat_name=chat_name,
        completions_name=completions_name,
    )


def create_sync_client(options: OpenAICompatibleSyncOptions) -> Any:
    if options.use_fake_openai:
        base_client: Any = FakeOpenAI()
    else:
        kwargs: dict[str, Any] = {}
        if options.base_url:
            kwargs["base_url"] = options.base_url
        if options.api_key:
            kwargs["api_key"] = options.api_key
        if options.default_headers:
            kwargs["default_headers"] = options.default_headers
        if options.timeout is not None:
            kwargs["timeout"] = options.timeout
        base_client = OpenAI(**kwargs)

    if not options.wrap_langsmith:
        return base_client

    return _wrap_openai_client(
        base_client,
        chat_name=options.chat_name,
        completions_name=options.completions_name,
    )


def create_async_client(options: OpenAICompatibleAsyncOptions) -> Any:
    if options.use_fake_openai:
        base_client: Any = FakeOpenAI()
    else:
        kwargs: dict[str, Any] = {}
        if options.base_url:
            kwargs["base_url"] = options.base_url
        if options.api_key:
            kwargs["api_key"] = options.api_key
        if options.default_headers:
            kwargs["default_headers"] = options.default_headers
        if options.timeout is not None:
            kwargs["timeout"] = options.timeout
        base_client = AsyncOpenAI(**kwargs)

    if not options.wrap_langsmith:
        return base_client

    return _wrap_openai_client(
        base_client,
        chat_name=options.chat_name,
        completions_name=options.completions_name,
    )
