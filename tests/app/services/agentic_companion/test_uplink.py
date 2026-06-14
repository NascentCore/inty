"""Uplink envelope parsing tests."""

from __future__ import annotations

from app.core.companion_harness.agent_channel.scope import AgentScope
from app.core.companion_harness.companion.runtime_channel import CompanionRuntimeChannel
from app.schemas.chat import ChatCompletionRequest, ChatMessage
from app.services.agentic_channel.telegram_uplink import parse_telegram_uplink
from backend.ops.weixin_channel.weixin_uplink import parse_weixin_uplink
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
    loop_channel = object()
    envelope = parse_ws_implicit_sign_on(
        user_id="u1",
        agent_id="a1",
        chat_id=10,
        preset_message_id="greet-mid",
        resolved_chat_model=model,
        session_id="sess",
        runtime_channel=CompanionRuntimeChannel.APP,
        client_time=None,
        agentic_loop_channel=loop_channel,
    )
    assert envelope.trigger == UplinkTriggerKind.IMPLICIT_SIGN_ON
    assert envelope.launch_ctx.preset_user_msg_uuid == "greet-mid"
    assert envelope.launch_ctx.agentic_loop_channel is loop_channel


def test_parse_telegram_uplink_runtime_channel() -> None:
    model = CHAT_TEXT_MODELS[0]
    scope = AgentScope(user_id="u1", agent_id="a1")
    envelope = parse_telegram_uplink(
        scope=scope,
        user_text="hi",
        resolved_chat_model=model,
        preset_user_msg_uuid="mid-tg",
        session_id="sess",
        runtime_channel=CompanionRuntimeChannel.TELEGRAM,
        background_output_sink=None,
        agentic_loop_channel=None,
    )
    assert envelope.trigger == UplinkTriggerKind.USER_MESSAGE
    assert envelope.runtime_context.channel == CompanionRuntimeChannel.TELEGRAM
    assert envelope.launch_ctx.runtime_channel == CompanionRuntimeChannel.TELEGRAM.value


def test_parse_weixin_uplink_trigger() -> None:
    model = CHAT_TEXT_MODELS[0]
    envelope = parse_weixin_uplink(
        user_id="u1",
        agent_id="a1",
        chat_id="wx-chat",
        user_text="hello wx",
        resolved_chat_model=model,
        session_id="sess",
        preset_user_msg_uuid="mid-wx",
        background_output_sink=None,
        agentic_loop_channel=None,
    )
    assert envelope.trigger == UplinkTriggerKind.USER_MESSAGE
    assert envelope.user_text() == "hello wx"
    assert envelope.runtime_context.channel == CompanionRuntimeChannel.WECHAT_WEIXIN
