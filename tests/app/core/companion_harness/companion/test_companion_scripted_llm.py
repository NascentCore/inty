"""Tests for companion_scripted_llm wiring and script builder."""

from __future__ import annotations

import pytest

from app.core.companion_harness.loop.config import UserTurnLlmLoopMode
from app.core.llms.client import CompanionLLMConfig
from app.external_services.fakes.openai import fake_step_text
from tests.app.core.companion_harness.companion.companion_scripted_llm import (
    SettledUserChatScriptScenario,
    assert_all_routes_share_fake,
    build_scripted_settled_user_chat_script,
    companion_llm_client_with_scripted_transport,
)


def test_companion_llm_client_with_scripted_transport_wires_all_routes() -> (
    None
):
    script = (fake_step_text("wired"),)
    client, fake = companion_llm_client_with_scripted_transport(
        CompanionLLMConfig(api_key="test-key"),
        script,
    )
    assert_all_routes_share_fake(client, fake)

    resp = client.chat_completion(
        messages=[{"role": "user", "content": "hi"}],
        scene="chat",
    )
    assert resp.choices[0].message.content == "wired"
    assert fake.script_index == 1


@pytest.mark.parametrize(
    ("mode", "expected_step_count"),
    [
        (UserTurnLlmLoopMode.DUAL_LLM, 2),
        (UserTurnLlmLoopMode.IN_TURN_SINGLE_LLM, 1),
    ],
)
def test_no_tools_script_step_counts(
    mode: UserTurnLlmLoopMode,
    expected_step_count: int,
) -> None:
    built = build_scripted_settled_user_chat_script(
        mode,
        SettledUserChatScriptScenario.NO_TOOLS,
    )
    assert built.mode == mode
    assert built.expected_step_count == expected_step_count
    assert len(built.steps) == expected_step_count
    assert built.expected_foreground_reply == "Hi, I'm here."


def test_dual_llm_tool_background_script_step_count() -> None:
    built = build_scripted_settled_user_chat_script(
        UserTurnLlmLoopMode.DUAL_LLM,
        SettledUserChatScriptScenario.DUAL_LLM_TOOL_BACKGROUND,
    )
    assert built.expected_step_count == 3
    assert len(built.steps) == 3
    assert built.expected_foreground_reply == "I'll list your scope root."


def test_dual_llm_silent_foreground_tool_bg_script_step_count() -> None:
    built = build_scripted_settled_user_chat_script(
        UserTurnLlmLoopMode.DUAL_LLM,
        SettledUserChatScriptScenario.DUAL_LLM_SILENT_FOREGROUND_TOOL_BG,
    )
    assert built.expected_step_count == 3
    assert len(built.steps) == 3
    assert built.expected_foreground_reply is None
