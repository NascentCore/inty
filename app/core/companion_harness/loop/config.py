"""Agentic loop mode selection for settled user turns."""

from __future__ import annotations

from enum import StrEnum


class UserTurnLlmLoopMode(StrEnum):
    """Which production AgenticLoop method settled user turns use."""

    IN_TURN_SINGLE_LLM = "in_turn_single_llm"
    DUAL_LLM = "dual_llm"


class AgenticLoopMechanism(StrEnum):
    """Loop execution mechanism; orthogonal to ``CompanionTurnTrack`` turn shape (#3401)."""

    SINGLE_LLM = "single_llm"
    DUAL_LLM = "dual_llm"


def agentic_loop_mechanism_from_user_turn_mode(
    mode: UserTurnLlmLoopMode,
) -> AgenticLoopMechanism:
    """Map config ``llm_loop_mode`` to ``AgenticLoopMechanism``."""
    match mode:
        case UserTurnLlmLoopMode.IN_TURN_SINGLE_LLM:
            return AgenticLoopMechanism.SINGLE_LLM
        case UserTurnLlmLoopMode.DUAL_LLM:
            return AgenticLoopMechanism.DUAL_LLM


class BatchUserMessagesLlmCallMode(StrEnum):
    """How one claimed InputQueue batch is represented in a user-turn LLM call."""

    JOIN_TO_ONE_USER_MESSAGE = "JOIN_TO_ONE_USER_MESSAGE"
    MULTI_USER_MESSAGES = "MULTI_USER_MESSAGES"


def resolved_user_turn_llm_loop_mode() -> UserTurnLlmLoopMode:
    """Read agent.companion_harness.user_turn.llm_loop_mode from global config."""
    from app.core.config import global_config_loaded_from_config_yaml

    raw = (
        global_config_loaded_from_config_yaml.agent.companion_harness.user_turn.llm_loop_mode
    )
    return UserTurnLlmLoopMode(raw)


def resolved_user_turn_batch_messages_llm_call_mode() -> (
    BatchUserMessagesLlmCallMode
):
    """Read agent.companion_harness.user_turn.batch_user_messages_llm_call_mode."""
    from app.core.config import global_config_loaded_from_config_yaml

    raw = (
        global_config_loaded_from_config_yaml.agent.companion_harness.user_turn.batch_user_messages_llm_call_mode
    )
    return BatchUserMessagesLlmCallMode(raw)


def resolved_companion_harness_reply_language() -> str | None:
    """Read agent.companion_harness.language; None means match user message language."""
    from app.core.config import global_config_loaded_from_config_yaml

    return (
        global_config_loaded_from_config_yaml.agent.companion_harness.language
    )
