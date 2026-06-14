"""Uplink envelope parsing tests."""

from __future__ import annotations

from app.core.companion_harness.companion.runtime_channel import CompanionRuntimeChannel
from app.schemas.chat import ChatCompletionRequest, ChatMessage
from app.services.agentic_companion.uplink import UplinkTriggerKind
from app.services.agentic_companion.ws_uplink import (
    parse_ws_implicit_sign_on,
    parse_ws_user_message,
)
from app.utils.models_catalog import CHAT_TEXT_MODELS


def test_parse_ws_user_message_trigger() -> None:
    model = CHAT_TEXT_MODELS[0]
    envelope = parse_ws_user_message(
        user_id="u1",
        agent_id="a1",
        chat_id=10,
        request=ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="hello")],
            message_id="mid-1",
        ),
        resolved_chat_model=model,
        session_id="sess",
        runtime_channel=CompanionRuntimeChannel.APP,
        implicit_signal_bundle=None,
        background_output_sink=None,
        bootstrap_interim_output_sink=None,
        agentic_loop_channel=None,
    )
    assert envelope.trigger == UplinkTriggerKind.USER_MESSAGE
    assert envelope.user_text() == "hello"


def test_parse_ws_implicit_sign_on_trigger() -> None:
    model = CHAT_TEXT_MODELS[0]
    envelope = parse_ws_implicit_sign_on(
        user_id="u1",
        agent_id="a1",
        chat_id=10,
        preset_message_id="greet-mid",
        resolved_chat_model=model,
        session_id="sess",
        runtime_channel=CompanionRuntimeChannel.APP,
        client_time=None,
    )
    assert envelope.trigger == UplinkTriggerKind.IMPLICIT_SIGN_ON
    assert envelope.launch_ctx.preset_user_msg_uuid == "greet-mid"
