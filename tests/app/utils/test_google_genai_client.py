from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

from app.core.config import Environment
from app.utils import google_genai_client


def test_wrap_google_genai_client_skips_when_environment_is_test(monkeypatch):
    original_client = object()
    fake_wrap = Mock(return_value="wrapped")

    monkeypatch.setattr(
        google_genai_client.global_config_loaded_from_config_yaml.app,
        "environment",
        Environment.TEST,
    )
    monkeypatch.setattr(
        google_genai_client,
        "langsmith_wrappers",
        SimpleNamespace(wrap_gemini=fake_wrap),
    )

    wrapped = google_genai_client.wrap_google_genai_client_with_langsmith(
        original_client,
        tags=["google-genai"],
        metadata={"source": "test"},
        chat_name="chat-name",
    )

    assert wrapped is original_client
    fake_wrap.assert_not_called()


def test_wrap_google_genai_client_passes_tracing_extra(monkeypatch):
    original_client = object()
    fake_wrap = Mock(return_value="wrapped-client")

    monkeypatch.setattr(
        google_genai_client.global_config_loaded_from_config_yaml.app,
        "environment",
        Environment.DEV,
    )
    monkeypatch.setattr(
        google_genai_client,
        "langsmith_wrappers",
        SimpleNamespace(wrap_gemini=fake_wrap),
    )

    wrapped = google_genai_client.wrap_google_genai_client_with_langsmith(
        original_client,
        tags=["google-genai", 42],  # type: ignore[list-item]
        metadata={
            "when": datetime(2026, 2, 20, 8, 30, 0),
            "nested": {"enabled": True},
        },
        chat_name="gemini-chat",
    )

    assert wrapped == "wrapped-client"
    fake_wrap.assert_called_once()

    call_args = fake_wrap.call_args
    assert call_args is not None
    args, kwargs = call_args
    assert args == (original_client,)
    assert kwargs["chat_name"] == "gemini-chat"
    assert kwargs["tracing_extra"]["tags"] == ["google-genai", "42"]
    assert kwargs["tracing_extra"]["metadata"]["when"] == "2026-02-20T08:30:00"
    assert kwargs["tracing_extra"]["metadata"]["nested"] == {"enabled": True}


def test_wrap_google_genai_client_falls_back_to_legacy_signature(monkeypatch):
    original_client = object()
    captured_kwargs: list[dict] = []

    def fake_wrap_gemini(client, **kwargs):
        captured_kwargs.append(kwargs)
        if kwargs:
            raise TypeError("unexpected keyword argument")
        return "legacy-wrapped"

    monkeypatch.setattr(
        google_genai_client.global_config_loaded_from_config_yaml.app,
        "environment",
        Environment.DEV,
    )
    monkeypatch.setattr(
        google_genai_client,
        "langsmith_wrappers",
        SimpleNamespace(wrap_gemini=fake_wrap_gemini),
    )

    wrapped = google_genai_client.wrap_google_genai_client_with_langsmith(
        original_client,
        tags=["google-genai"],
        metadata={"source": "legacy-test"},
        chat_name="legacy-chat",
    )

    assert wrapped == "legacy-wrapped"
    assert len(captured_kwargs) == 2
    assert "tracing_extra" in captured_kwargs[0]
    assert "chat_name" in captured_kwargs[0]
    assert captured_kwargs[1] == {}


def test_wrap_google_genai_client_returns_original_when_wrap_missing(
    monkeypatch,
):
    original_client = object()

    monkeypatch.setattr(
        google_genai_client.global_config_loaded_from_config_yaml.app,
        "environment",
        Environment.DEV,
    )
    monkeypatch.setattr(
        google_genai_client,
        "langsmith_wrappers",
        SimpleNamespace(),
    )

    wrapped = google_genai_client.wrap_google_genai_client_with_langsmith(
        original_client,
        tags=["google-genai"],
    )

    assert wrapped is original_client
