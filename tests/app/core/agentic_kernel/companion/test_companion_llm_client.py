from __future__ import annotations

from typing import Any

import pytest

from app.core.agentic_kernel.companion import llm_client as llm_client_module
from app.core.agentic_kernel.companion.llm_client import (
    CompanionLLMClient,
    CompanionLLMConfig,
)
from app.core.agentic_kernel.providers.facade import OpenAICompatibleClientOptions


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

    chat_names = [options.chat_name for options in captured_options]
    assert chat_names == [
        "companion_unified_chat",
        "companion_dual_chat",
        "companion_dual_tool",
    ]
    assert len(set(chat_names)) == len(chat_names)
