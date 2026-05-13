"""Regression coverage for the Gemini provider cache and construction options."""

from __future__ import annotations

import os
from typing import Any

import pytest

from app.core.companion_harness.providers import gemini
from app.core.companion_harness.providers.gemini import (
    GeminiClientOptions,
    get_gemini_client,
)


@pytest.fixture(autouse=True)
def _clear_gemini_provider_cache() -> None:
    gemini._CLIENT_CACHE.clear()
    yield
    gemini._CLIENT_CACHE.clear()


def test_vertex_client_uses_cache_and_credentials_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    calls: list[dict[str, Any]] = []

    def _fake_client(**kwargs: Any) -> object:
        calls.append(kwargs)
        return object()

    credentials_path = tmp_path / "service-account.json"
    credentials_path.write_text("{}", encoding="utf-8")
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.setattr(gemini.genai, "Client", _fake_client)

    options = GeminiClientOptions(
        vertexai=True,
        project="inty-test-project",
        location="us-central1",
        credentials_path=str(credentials_path),
    )

    client_1 = get_gemini_client(options)
    client_2 = get_gemini_client(options)

    assert client_1 is client_2
    assert len(calls) == 1
    assert calls[0] == {
        "vertexai": True,
        "project": "inty-test-project",
        "location": "us-central1",
    }
    assert os.environ["GOOGLE_APPLICATION_CREDENTIALS"] == str(credentials_path)


def test_newapi_options_clear_google_env_and_use_provider_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setenv("GOOGLE_API_KEY", "ambient-google-key")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/tmp/ambient-creds.json")

    def _fake_client(**kwargs: Any) -> object:
        assert "GOOGLE_API_KEY" not in os.environ
        assert "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ
        calls.append(kwargs)
        return object()

    monkeypatch.setattr(gemini.genai, "Client", _fake_client)
    options = GeminiClientOptions(
        api_key="newapi-token",
        http_options={
            "api_version": "v1beta",
            "headers": {"Authorization": "Bearer newapi-token"},
            "base_url": "https://newapi.example.com",
        },
        clear_google_env=True,
    )

    client_1 = get_gemini_client(options)
    client_2 = get_gemini_client(options)

    assert client_1 is client_2
    assert len(calls) == 1
    assert calls[0]["api_key"] == "newapi-token"
    http_options = calls[0]["http_options"]
    assert http_options.base_url == "https://newapi.example.com"
    assert http_options.api_version == "v1beta"
    assert http_options.headers["Authorization"] == "Bearer newapi-token"
    assert os.environ["GOOGLE_API_KEY"] == "ambient-google-key"
    assert os.environ["GOOGLE_APPLICATION_CREDENTIALS"] == "/tmp/ambient-creds.json"


def test_http_option_cache_key_is_order_insensitive_and_value_sensitive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    def _fake_client(**kwargs: Any) -> object:
        calls.append(kwargs)
        return object()

    monkeypatch.setattr(gemini.genai, "Client", _fake_client)

    first = get_gemini_client(
        GeminiClientOptions(
            api_key="token",
            http_options={
                "base_url": "https://newapi.example.com",
                "headers": {"X-Test": "one", "Authorization": "Bearer token"},
            },
            clear_google_env=True,
        )
    )
    same = get_gemini_client(
        GeminiClientOptions(
            api_key="token",
            http_options={
                "headers": {"Authorization": "Bearer token", "X-Test": "one"},
                "base_url": "https://newapi.example.com",
            },
            clear_google_env=True,
        )
    )
    different = get_gemini_client(
        GeminiClientOptions(
            api_key="token",
            http_options={
                "base_url": "https://different.example.com",
                "headers": {"Authorization": "Bearer token", "X-Test": "one"},
            },
            clear_google_env=True,
        )
    )

    assert first is same
    assert first is not different
    assert len(calls) == 2


def test_langsmith_wrapped_client_is_cached_by_trace_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_client = object()
    wrapped_client = object()
    wrap_calls: list[dict[str, Any]] = []

    monkeypatch.setattr(gemini.genai, "Client", lambda **_: base_client)

    def _fake_wrap(client: object, **kwargs: Any) -> object:
        wrap_calls.append({"client": client, **kwargs})
        return wrapped_client

    monkeypatch.setattr(gemini, "wrap_google_genai_client_with_langsmith", _fake_wrap)

    options = GeminiClientOptions(
        api_key="token",
        wrap_langsmith=True,
        tags=("gemini", "provider-test"),
        metadata={"source": "test"},
        chat_name="GeminiProviderTest",
    )

    client_1 = get_gemini_client(options)
    client_2 = get_gemini_client(options)

    assert client_1 is wrapped_client
    assert client_2 is wrapped_client
    assert wrap_calls == [
        {
            "client": base_client,
            "tags": ["gemini", "provider-test"],
            "metadata": {"source": "test"},
            "chat_name": "GeminiProviderTest",
        }
    ]
