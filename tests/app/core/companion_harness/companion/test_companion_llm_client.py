from __future__ import annotations

from typing import Any

import pytest

from app.core.companion_harness.companion import llm_client as llm_client_module
from app.core.companion_harness.companion.llm_client import (
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
