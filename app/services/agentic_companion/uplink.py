"""Uplink envelope: channel-agnostic user-turn entry into Session hub."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.core.companion_harness.companion.runtime_channel import TurnRuntimeContext
from app.utils.models_catalog import GenAIModel


class UplinkTriggerKind(StrEnum):
    """What caused this user-turn uplink (orthogonal to bootstrap/settled harness phase)."""

    USER_MESSAGE = "user_message"
    IMPLICIT_SIGN_ON = "implicit_sign_on"


class TurnLaunchContext(BaseModel):
    """Per-turn launch facts shared by all channels."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    user_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    chat_id: str | int
    resolved_chat_model: GenAIModel
    session_id: str | None = None
    preset_user_msg_uuid: str | None = None
    runtime_channel: str
    background_output_sink: object | None = None
    bootstrap_interim_output_sink: object | None = None
    agentic_loop_channel: object | None = None


class UplinkEnvelope(BaseModel):
    """One user-turn uplink before Session dispatch."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    trigger: UplinkTriggerKind
    user_input: object
    launch_ctx: TurnLaunchContext
    runtime_context: TurnRuntimeContext

    def user_text(self) -> str:
        """Extract plain user text from ``user_input``."""
        from app.core.companion_harness.companion.user_turn_input import (
            CompanionUserTurnInput,
        )

        assert isinstance(self.user_input, CompanionUserTurnInput)
        return self.user_input.to_transcript_text()
