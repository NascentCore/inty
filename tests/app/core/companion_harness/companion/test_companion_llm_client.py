from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.llms import client as llm_client_module
from app.core.llms.client import (
    AsyncLlmClient,
    CompanionLLMClient,
    CompanionLLMConfig,
)
from app.core.companion_harness.providers.openai_compatible_clients import (
    OpenAICompatibleClientOptions,
)


@pytest.mark.asyncio
async def test_async_llm_client_is_distinct_class_with_chat_completion() -> (
    None
):
    assert AsyncLlmClient is not CompanionLLMClient
    captured: dict[str, Any] = {}

    class _FakeCompletions:
        async def create(self, **kwargs: Any) -> Any:
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
            )

    class _FakeChat:
        completions = _FakeCompletions()

    class _FakeAsyncClient:
        chat = _FakeChat()

    client = AsyncLlmClient(CompanionLLMConfig(api_key="test-key"))
    client._async_client = _FakeAsyncClient()  # noqa: SLF001
    messages = [{"role": "user", "content": "hi"}]
    tools = [{"type": "function", "function": {"name": "generate_image"}}]
    result = await client.chat_completion(
        messages=messages,
        tools=tools,
        tool_choice=None,
        high_reasoning=True,
    )

    assert captured["messages"] == messages
    assert captured["tools"] == tools
    assert "tool_choice" not in captured
    assert captured["parallel_tool_calls"] is True
    assert captured["extra_body"] == {
        "reasoning": {"effort": "high", "exclude": True}
    }
    assert result.choices[0].message.content == "ok"


@pytest.mark.asyncio
async def test_async_llm_client_passes_langsmith_extra() -> None:
    captured: dict[str, Any] = {}

    class _FakeCompletions:
        async def create(self, **kwargs: Any) -> Any:
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
            )

    class _FakeChat:
        completions = _FakeCompletions()

    class _FakeAsyncClient:
        chat = _FakeChat()

    client = AsyncLlmClient(CompanionLLMConfig(api_key="test-key"))
    client._async_client = _FakeAsyncClient()  # noqa: SLF001
    langsmith_extra = {
        "metadata": {"inty_llm_source": "single_completion"},
    }
    await client.chat_completion(
        messages=[{"role": "user", "content": "hi"}],
        tools=[],
        tool_choice=None,
        langsmith_extra=langsmith_extra,
    )

    assert captured["langsmith_extra"] == langsmith_extra


def test_companion_llm_client_reuses_async_llm_client() -> None:
    companion = CompanionLLMClient(CompanionLLMConfig(api_key="test-key"))
    first = companion.async_llm_client
    second = companion.async_llm_client
    assert first is second


def test_async_llm_client_instances_share_cached_http_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.companion_harness.providers import (
        openai_compatible_clients as occ_mod,
    )

    build_count = 0
    original_build = occ_mod._build_openai_compatible_async_client

    def _counting_build(options: OpenAICompatibleClientOptions) -> Any:
        nonlocal build_count
        build_count += 1
        return original_build(options=options)

    with occ_mod._CLIENT_CACHE_LOCK:
        occ_mod._CLIENT_CACHE.clear()
    monkeypatch.setattr(
        occ_mod,
        "_build_openai_compatible_async_client",
        _counting_build,
    )
    cfg = CompanionLLMConfig(api_key="test-key")
    first = AsyncLlmClient(cfg)
    second = AsyncLlmClient(cfg)

    assert first._async_client is second._async_client  # noqa: SLF001
    assert build_count == 1


def test_async_llm_client_uses_langsmith_wrapper_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_options: list[OpenAICompatibleClientOptions] = []

    def _fake_get_client(options: OpenAICompatibleClientOptions) -> Any:
        captured_options.append(options)
        return object()

    monkeypatch.setattr(
        llm_client_module,
        "get_openai_compatible_async_client",
        _fake_get_client,
    )

    AsyncLlmClient(CompanionLLMConfig(api_key="test-key"))

    assert len(captured_options) == 1
    options = captured_options[0]
    assert options.wrap_langsmith is True
    assert options.chat_name == "agentic_companion_async_chat"
    assert options.completions_name == "companion_AsyncOpenAI"


def test_companion_llm_clients_use_distinct_langsmith_chat_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_options: list[OpenAICompatibleClientOptions] = []

    def _fake_get_client(options: OpenAICompatibleClientOptions) -> Any:
        captured_options.append(options)
        return object()

    monkeypatch.setattr(
        llm_client_module,
        "get_openai_compatible_sync_client",
        _fake_get_client,
    )

    client = CompanionLLMClient(CompanionLLMConfig(api_key="test-key"))
    client.sync_client_for_route("chat")
    client.sync_client_for_route("tool")
    client.sync_client_for_route("inner_tick")

    chat_names = [options.chat_name for options in captured_options]
    assert chat_names == [
        "agentic_companion_unified_chat",
        "agentic_companion_chat",
        "agentic_companion_tool_call",
        "agentic_companion_inner_tick",
    ]
    assert len(set(chat_names)) == len(chat_names)


def test_complete_text_passes_dreaming_consolidation_langsmith_extra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def _fake_sync(
        client: Any,
        *,
        model: str,
        messages_payload: list,
        tools: list,
        tool_choice: str | None = None,
        response_format: dict | None = None,
        langsmith_extra: dict[str, Any] | None = None,
    ) -> Any:
        captured["langsmith_extra"] = langsmith_extra

        class _Msg:
            content = "curated"

        class _Choice:
            message = _Msg()

        class _Resp:
            choices = [_Choice()]

        return _Resp()

    monkeypatch.setattr(
        llm_client_module, "create_chat_completion_sync", _fake_sync
    )
    monkeypatch.setattr(
        llm_client_module,
        "get_openai_compatible_sync_client",
        lambda *_a, **_k: object(),
    )

    client = CompanionLLMClient(CompanionLLMConfig(api_key="test-key"))
    out = client.complete_text(
        [{"role": "user", "content": "hello"}],
        model_role="day_summary",
    )
    assert out == "curated"
    extra = captured.get("langsmith_extra") or {}
    assert (
        extra.get("name")
        == "agentic_companion_dreaming_consolidation-day_summary"
    )
    meta = extra.get("metadata") or {}
    assert meta.get("inty_llm_source") == "dreaming_consolidation_day_summary"


def _ok_completion() -> Any:
    msg = SimpleNamespace(content="ok", tool_calls=[])
    return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


@pytest.mark.asyncio
async def test_chat_completion_with_retrial_succeeds_after_transient_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = CompanionLLMClient(CompanionLLMConfig(api_key="test-key"))
    calls = 0

    def _flaky(**_kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("transient")
        return _ok_completion()

    monkeypatch.setattr(client, "chat_completion", _flaky)
    out = await client.chat_completion_with_retrial(
        messages=[{"role": "user", "content": "hi"}],
        model=None,
        tools=None,
        tool_choice=None,
        response_format=None,
        scene="chat",
        langsmith_extra=None,
        high_reasoning=False,
        max_attempts=2,
        per_attempt_timeout_sec=30.0,
        trace_id="trace-1",
        attempt_log_label="test_retrial",
    )

    assert out.choices[0].message.content == "ok"
    assert calls == 2


@pytest.mark.asyncio
async def test_chat_completion_with_retrial_times_out_per_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = CompanionLLMClient(CompanionLLMConfig(api_key="test-key"))
    calls = 0

    def _slow(**_kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        time.sleep(0.25)
        return _ok_completion()

    monkeypatch.setattr(client, "chat_completion", _slow)
    with pytest.raises(asyncio.TimeoutError):
        await client.chat_completion_with_retrial(
            messages=[{"role": "user", "content": "hi"}],
            model=None,
            tools=None,
            tool_choice=None,
            response_format=None,
            scene="chat",
            langsmith_extra=None,
            high_reasoning=False,
            max_attempts=2,
            per_attempt_timeout_sec=0.1,
            trace_id="trace-2",
            attempt_log_label="test_retrial",
        )

    assert calls == 2


@pytest.mark.asyncio
async def test_create_chat_completion_sync_json_retry_is_separate() -> None:
    """OpenAI path retries JSONDecodeError only; not a substitute for with_retrial."""
    from app.core.companion_harness.llm import chat_completions as cc_mod

    assert cc_mod._OPENROUTER_JSON_MAX_ATTEMPTS == 3
