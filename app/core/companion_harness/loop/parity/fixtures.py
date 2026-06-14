"""Fake LLM clients and response builders for loop parity smoke (no test imports)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

from app.core.companion_harness.companion.llm_client import CompanionLLMConfig
from app.utils.models_catalog import GenAIModel, resolve_chat_text_model


def tool_response(
    *,
    content: str,
    tool_name: str,
    tool_arguments: str,
) -> SimpleNamespace:
    """OpenAI-style completion with one tool call."""
    function = SimpleNamespace(name=tool_name, arguments=tool_arguments)
    tool_call = SimpleNamespace(id="tc-1", type="function", function=function)
    message = SimpleNamespace(content=content, tool_calls=[tool_call])
    choice = SimpleNamespace(message=message, finish_reason="tool_calls")
    return SimpleNamespace(choices=[choice], model="test-model", usage=None)


def final_response(*, content: str) -> SimpleNamespace:
    """OpenAI-style terminal assistant completion."""
    message = SimpleNamespace(content=content, tool_calls=None)
    choice = SimpleNamespace(message=message, finish_reason="stop")
    return SimpleNamespace(choices=[choice], model="test-model", usage=None)


class FakeSyncToolLoopLLMClient:
    """Fake chat client for 1-LLM in-turn sync tool loop parity."""

    def __init__(self, responses: list[SimpleNamespace]) -> None:
        self.config = CompanionLLMConfig(api_base="https://example.invalid/v1")
        self._responses = iter(responses)
        self.tools_per_call: list[tuple[dict[str, Any], ...]] = []

    def resolve_model(self, role: str) -> GenAIModel:
        return resolve_chat_text_model(f"test/{role}")

    def chat_completion(self, **kwargs: Any) -> SimpleNamespace:
        tools = kwargs.get("tools")
        self.tools_per_call.append(tuple(tools) if tools is not None else ())
        return next(self._responses)


def dual_llm_envelope_content(*, user_facing_reply: str) -> str:
    """JSON envelope for dual-LLM foreground chat fake responses."""
    payload = {
        "user_facing_reply": user_facing_reply,
        "output_to_user": True,
        "importance_round": 5,
        "importance_user_message": 5,
        "importance_assistant_message": 5,
        "turn_recall": "brief",
    }
    return json.dumps(payload)


def dual_llm_fg_response(*, text: str) -> SimpleNamespace:
    """Foreground chat completion for dual-LLM parity."""
    message = SimpleNamespace(
        content=dual_llm_envelope_content(user_facing_reply=text),
        tool_calls=None,
    )
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def dual_llm_tool_finish_response() -> SimpleNamespace:
    """Tool-leg completion with no user-visible output."""
    envelope = {
        "user_facing_reply": "",
        "output_to_user": False,
        "importance_round": 1,
        "importance_user_message": 1,
        "importance_assistant_message": 1,
    }
    message = SimpleNamespace(
        content=json.dumps(envelope),
        tool_calls=[],
    )
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeDualLlmClient:
    """Fake chat + tool sync client for dual-LLM sidecar parity."""

    def __init__(
        self,
        *,
        fg_response: SimpleNamespace,
        tool_sync_handler: object | None,
    ) -> None:
        self.config = CompanionLLMConfig(
            api_base="https://example.invalid/v1",
            async_chat_front_timeout_sec=30.0,
        )
        self._fg_response = fg_response
        self.chat_completions_sync = tool_sync_handler
        self.fg_called = False

    def resolve_model(self, role: str) -> GenAIModel:
        return resolve_chat_text_model(f"test/{role}")

    def chat_completion(self, **kwargs: Any) -> SimpleNamespace:
        self.fg_called = True
        return self._fg_response

    def sync_client_for_route(self, route: str) -> object:
        assert route == "tool"
        return object()
