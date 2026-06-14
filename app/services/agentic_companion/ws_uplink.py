"""WebSocket uplink parsers → ``UplinkEnvelope``."""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.companion_harness.companion.runtime_channel import (
    CompanionRuntimeChannel,
    TurnRuntimeContext,
)
from app.core.companion_harness.companion.user_turn_input import CompanionUserTurnInput
from app.schemas.chat import ChatCompletionRequest
from app.schemas.implicit_signals import ImplicitSignalBundle
from app.utils.models_catalog import GenAIModel

from .uplink import TurnLaunchContext, UplinkEnvelope, UplinkTriggerKind


def parse_ws_user_message(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    request: ChatCompletionRequest,
    resolved_chat_model: GenAIModel,
    session_id: str | None,
    runtime_channel: CompanionRuntimeChannel,
    implicit_signal_bundle: ImplicitSignalBundle | None,
    background_output_sink: object | None,
    bootstrap_interim_output_sink: object | None,
    agentic_loop_channel: object | None,
) -> UplinkEnvelope:
    """Map one WS chat completion request to ``USER_MESSAGE`` uplink."""
    last_user_msg = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            last_user_msg = msg
            break
    assert last_user_msg is not None
    last_user = last_user_msg.extract_text_content()
    assert last_user.strip()
    preset_uid = (request.message_id or "").strip() or None
    bundle = implicit_signal_bundle or ImplicitSignalBundle(
        client_time=request.user_time_context,
        user_signed_on=False,
        server_received_at_utc=datetime.now(timezone.utc),
    )
    return UplinkEnvelope(
        trigger=UplinkTriggerKind.USER_MESSAGE,
        user_input=CompanionUserTurnInput(text=last_user),
        launch_ctx=TurnLaunchContext(
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat_id,
            resolved_chat_model=resolved_chat_model,
            session_id=session_id,
            preset_user_msg_uuid=preset_uid,
            runtime_channel=runtime_channel.value,
            background_output_sink=background_output_sink,
            bootstrap_interim_output_sink=bootstrap_interim_output_sink,
            agentic_loop_channel=agentic_loop_channel,
        ),
        runtime_context=TurnRuntimeContext(
            channel=runtime_channel,
            implicit_signal_bundle=bundle,
        ),
    )


def parse_ws_implicit_sign_on(
    *,
    user_id: str,
    agent_id: str,
    chat_id: str | int,
    preset_message_id: str,
    resolved_chat_model: GenAIModel,
    session_id: str | None,
    runtime_channel: CompanionRuntimeChannel,
    client_time: object | None,
    agentic_loop_channel: object | None,
) -> UplinkEnvelope:
    """Map WS ``user_signed_on`` greeting to ``IMPLICIT_SIGN_ON`` uplink."""
    assert preset_message_id.strip()
    bundle = ImplicitSignalBundle(
        client_time=client_time,
        user_signed_on=True,
        server_received_at_utc=datetime.now(timezone.utc),
    )
    return UplinkEnvelope(
        trigger=UplinkTriggerKind.IMPLICIT_SIGN_ON,
        user_input=CompanionUserTurnInput(text=""),
        launch_ctx=TurnLaunchContext(
            user_id=user_id,
            agent_id=agent_id,
            chat_id=chat_id,
            resolved_chat_model=resolved_chat_model,
            session_id=session_id,
            preset_user_msg_uuid=preset_message_id.strip(),
            runtime_channel=runtime_channel.value,
            background_output_sink=None,
            bootstrap_interim_output_sink=None,
            agentic_loop_channel=agentic_loop_channel,
        ),
        runtime_context=TurnRuntimeContext(
            channel=runtime_channel,
            implicit_signal_bundle=bundle,
        ),
    )
