"""Agentic loop mode selection (aligned with #3369 ``user_turn.llm_loop_mode`` draft)."""

from __future__ import annotations

from enum import StrEnum

from .one_llm.mechanism import OneModelInTurnSyncMechanism
from .two_llm.mechanism import TwoModelChatThenToolBgMechanism


class UserTurnLlmLoopMode(StrEnum):
    """Which agentic loop mechanism settled user turns use (sidecar + future #3369)."""

    IN_TURN_SINGLE_LLM = "in_turn_single_llm"
    DUAL_LLM = "dual_llm"


def resolve_agentic_loop(mode: UserTurnLlmLoopMode) -> OneModelInTurnSyncMechanism | TwoModelChatThenToolBgMechanism:
    """Return the mechanism implementation for ``mode`` (sole config branch site)."""
    match mode:
        case UserTurnLlmLoopMode.IN_TURN_SINGLE_LLM:
            return OneModelInTurnSyncMechanism()
        case UserTurnLlmLoopMode.DUAL_LLM:
            return TwoModelChatThenToolBgMechanism()
