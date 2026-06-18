"""Agentic loop mode selection for settled user turns."""

from __future__ import annotations

from enum import StrEnum


class UserTurnLlmLoopMode(StrEnum):
    """Which production AgenticLoop method settled user turns use."""

    IN_TURN_SINGLE_LLM = "in_turn_single_llm"
    DUAL_LLM = "dual_llm"


def resolved_user_turn_llm_loop_mode() -> UserTurnLlmLoopMode:
    """Read agent.companion_harness.user_turn.llm_loop_mode from global config."""
    from app.core.config import global_config_loaded_from_config_yaml

    raw = (
        global_config_loaded_from_config_yaml.agent.companion_harness.user_turn.llm_loop_mode
    )
    return UserTurnLlmLoopMode(raw)
