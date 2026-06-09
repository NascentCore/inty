from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.companion_harness.companion import llm_client as llm_client_module
from app.core.companion_harness.companion.llm_client import (
    CompanionLLMClient,
    CompanionLLMConfig,
)
from app.infra.openai_compatible.client_cache import (
    OpenAICompatibleClientOptions,
    get_openai_compatible_async_client,
)


def test_companion_llm_clients_use_distinct_langsmith_chat_names(
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

    client = CompanionLLMClient(CompanionLLMConfig(api_key="test-key"))
    client.async_client_for_route("chat")
    client.async_client_for_route("tool")
    client.async_client_for_route("inner_tick")

    chat_names = [options.chat_name for options in captured_options]
    assert chat_names == [
        "agentic_companion_unified_chat",
        "agentic_companion_chat",
        "agentic_companion_tool_call",
        "agentic_companion_inner_tick",
    ]
    assert len(set(chat_names)) == len(chat_names)


@pytest.mark.asyncio
async def test_complete_text_passes_memory_pipeline_langsmith_extra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    async def _fake_create(
        client: Any,
        *,
        model: str,
        messages_payload: list,
        tools: list,
        tool_choice: str | None = None,
        response_format: dict | None = None,
        langsmith_extra: dict[str, Any] | None = None,
        high_reasoning: bool = False,
        on_inference_failure: Any = None,
        provider_kwargs: dict[str, Any] | None = None,
    ) -> Any:
        captured["langsmith_extra"] = langsmith_extra

        class _Msg:
            content = "curated"

        class _Choice:
            message = _Msg()

        class _Resp:
            choices = [_Choice()]

        return _Resp()

    monkeypatch.setattr(llm_client_module, "create_chat_completion", _fake_create)
    monkeypatch.setattr(
        llm_client_module,
        "get_openai_compatible_async_client",
        lambda *_a, **_k: object(),
    )

    client = CompanionLLMClient(CompanionLLMConfig(api_key="test-key"))
    out = await client.complete_text(
        [{"role": "user", "content": "hello"}],
        model_role="day_summary",
    )
    assert out == "curated"
    extra = captured.get("langsmith_extra") or {}
    assert extra.get("name") == "agentic_companion_memory_pipeline-day_summary"
    meta = extra.get("metadata") or {}
    assert meta.get("inty_llm_source") == "memory_pipeline_day_summary"


def _ok_completion() -> Any:
    msg = SimpleNamespace(content="ok", tool_calls=[])
    return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


@pytest.mark.asyncio
async def test_chat_completion_with_retrial_succeeds_after_transient_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = CompanionLLMClient(CompanionLLMConfig(api_key="test-key"))
    calls = 0

    async def _flaky(**_kwargs: Any) -> Any:
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

    async def _slow(**_kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.25)
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
async def test_create_chat_completion_json_retry_is_separate() -> None:
    """OpenAI path retries JSONDecodeError only; not a substitute for with_retrial."""
    from app.infra.openai_compatible import chat_completions as cc_mod

    assert cc_mod._OPENROUTER_JSON_MAX_ATTEMPTS == 3
