"""Tests for ``run_dual_llm_foreground_chat``."""

from __future__ import annotations

import json
import time
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.companion_harness.companion.dual_llm_foreground_chat import (
    build_chat_track_handoff_assistant_message,
    DualLlmForegroundChatInput,
    run_dual_llm_foreground_chat,
)
from app.core.companion_harness.companion.langsmith_turn_slice import (
    CompanionTurnLangsmithSlice,
)
from app.core.llms.client import (
    CompanionLLMConfig,
    LLM_SCENE_CHAT,
)
from app.core.companion_harness.companion.runtime_channel import (
    ChannelKind,
    TurnRuntimeContext,
)
from app.utils.models_catalog import resolve_chat_text_model


def _envelope_content(*, user_facing_reply: str) -> str:
    payload = {
        "user_facing_reply": user_facing_reply,
        "output_to_user": True,
        "importance_round": 5,
        "importance_user_message": 5,
        "importance_assistant_message": 5,
        "turn_recall": "brief note",
    }
    return json.dumps(payload)


class _FakeForegroundLLMClient:
    def __init__(self, response: SimpleNamespace) -> None:
        self.config = CompanionLLMConfig(
            api_base="https://example.invalid/v1",
            async_chat_front_timeout_sec=30.0,
        )
        self._response = response
        self.last_chat_kwargs: dict[str, Any] | None = None

    def chat_completion(self, **kwargs: Any) -> SimpleNamespace:
        self.last_chat_kwargs = dict(kwargs)
        return self._response


def _foreground_input(
    *,
    llm_client: _FakeForegroundLLMClient,
    skip_foreground_envelope: bool,
) -> DualLlmForegroundChatInput:
    chat_model = resolve_chat_text_model("test/chat")
    langsmith_slice = CompanionTurnLangsmithSlice.from_runtime_context(
        TurnRuntimeContext(
            channel=ChannelKind.APP_WS,
            implicit_signal_bundle=None,
        )
    )
    return DualLlmForegroundChatInput(
        llm_client=llm_client,  # type: ignore[arg-type]
        chat_msgs=({"role": "user", "content": "hi"},),
        tool_msgs=({"role": "user", "content": "hi"},),
        chat_model=chat_model,
        langsmith_slice=langsmith_slice,
        foreground_scene=LLM_SCENE_CHAT,
        high_reasoning=False,
        trace_id="trace-fg",
        skip_foreground_envelope=skip_foreground_envelope,
        langsmith_trace_id="",
        langsmith_run_id="",
    )


@pytest.mark.asyncio
async def test_run_dual_llm_foreground_chat_skip_envelope() -> None:
    llm_client = _FakeForegroundLLMClient(
        SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace())])
    )
    result = await run_dual_llm_foreground_chat(
        _foreground_input(
            llm_client=llm_client,
            skip_foreground_envelope=True,
        )
    )
    assert result.assistant_text == ""
    assert result.significance_meta is None
    assert result.turn_recall is None
    assert result.force_tools_first_round is True
    assert result.tool_msgs_for_bg == ({"role": "user", "content": "hi"},)
    assert llm_client.last_chat_kwargs is None


@pytest.mark.asyncio
async def test_run_dual_llm_foreground_chat_handoff_appends_chat_track_row() -> (
    None
):
    message = SimpleNamespace(
        content=_envelope_content(user_facing_reply="foreground ok"),
        tool_calls=None,
    )
    llm_client = _FakeForegroundLLMClient(
        SimpleNamespace(choices=[SimpleNamespace(message=message)])
    )
    result = await run_dual_llm_foreground_chat(
        _foreground_input(
            llm_client=llm_client,
            skip_foreground_envelope=False,
        )
    )
    assert result.assistant_text == "foreground ok"
    assert result.significance_meta is not None
    assert result.turn_recall == "brief note"
    assert result.force_tools_first_round is False
    handoff_rows = list(result.tool_msgs_for_bg)
    assert handoff_rows[-1] == build_chat_track_handoff_assistant_message(
        fg_text="foreground ok"
    )
    assert llm_client.last_chat_kwargs is not None
    assert llm_client.last_chat_kwargs["tools"] is None


@pytest.mark.asyncio
async def test_run_dual_llm_foreground_chat_empty_fg_forces_tools_first_round() -> (
    None
):
    message = SimpleNamespace(
        content=_envelope_content(user_facing_reply=""),
        tool_calls=None,
    )
    llm_client = _FakeForegroundLLMClient(
        SimpleNamespace(choices=[SimpleNamespace(message=message)])
    )
    result = await run_dual_llm_foreground_chat(
        _foreground_input(
            llm_client=llm_client,
            skip_foreground_envelope=False,
        )
    )
    assert result.assistant_text == ""
    assert result.force_tools_first_round is True
    assert len(result.tool_msgs_for_bg) == 1


class _SlowForegroundLLMClient:
    def __init__(self) -> None:
        self.config = CompanionLLMConfig.model_construct(
            api_base="https://example.invalid/v1",
            async_chat_front_timeout_sec=0.05,
        )

    def chat_completion(self, **kwargs: Any) -> SimpleNamespace:
        time.sleep(0.1)
        message = SimpleNamespace(content="", tool_calls=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


@pytest.mark.asyncio
async def test_run_dual_llm_foreground_chat_timeout_raises() -> None:
    with pytest.raises(RuntimeError, match="async chat front timed out"):
        await run_dual_llm_foreground_chat(
            _foreground_input(
                llm_client=_SlowForegroundLLMClient(),  # type: ignore[arg-type]
                skip_foreground_envelope=False,
            )
        )
