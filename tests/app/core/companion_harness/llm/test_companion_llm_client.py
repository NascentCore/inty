from __future__ import annotations

from typing import Any

import pytest

from app.core.companion_harness.llm import llm_client as llm_client_module
from app.core.companion_harness.llm.llm_client import (
    CompanionLLMClient,
    CompanionLLMConfig,
)
from app.core.companion_harness.providers.openai_compatible_clients import OpenAICompatibleClientOptions


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


def test_complete_text_passes_memory_pipeline_langsmith_extra(
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

    monkeypatch.setattr(llm_client_module, "create_chat_completion_sync", _fake_sync)
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
    assert extra.get("name") == "agentic_companion_memory_pipeline-day_summary"
    meta = extra.get("metadata") or {}
    assert meta.get("inty_llm_source") == "memory_pipeline_day_summary"
