"""Agentic loop mode selection (aligned with #3369 ``user_turn.llm_loop_mode`` draft).

TODO(#3460): Keep UserTurnLlmLoopMode as the config enum, but delete
resolve_agentic_loop() when sidecar mechanisms are retired.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .one_llm.mechanism import OneModelInTurnSyncMechanism
    from .two_llm.mechanism import TwoModelChatThenToolBgMechanism


class UserTurnLlmLoopMode(StrEnum):
    """Which agentic loop mechanism settled user turns use (sidecar + future #3369)."""

    IN_TURN_SINGLE_LLM = "in_turn_single_llm"
    DUAL_LLM = "dual_llm"


def resolved_user_turn_llm_loop_mode() -> UserTurnLlmLoopMode:
    """Read ``agent.companion_harness.user_turn.llm_loop_mode`` from global config."""
    from app.core.config import global_config_loaded_from_config_yaml

    raw = (
        global_config_loaded_from_config_yaml.agent.companion_harness.user_turn.llm_loop_mode
    )
    return UserTurnLlmLoopMode(raw)


def resolve_agentic_loop(
    mode: UserTurnLlmLoopMode,
) -> OneModelInTurnSyncMechanism | TwoModelChatThenToolBgMechanism:
    """Return the mechanism implementation for ``mode`` (legacy parity tests only).

    TODO(#3460): Remove after 1/2-LLM mechanism deletion; production dispatches
    directly to AgenticLoop user-turn methods.
    """
    from .one_llm.mechanism import OneModelInTurnSyncMechanism
    from .two_llm.mechanism import TwoModelChatThenToolBgMechanism

    match mode:
        case UserTurnLlmLoopMode.IN_TURN_SINGLE_LLM:
            return OneModelInTurnSyncMechanism()
        case UserTurnLlmLoopMode.DUAL_LLM:
            return TwoModelChatThenToolBgMechanism()
