"""LLM request leg identity within a companion turn.

Settled user turns use ``SINGLE_LLM`` in ``TurnComposeContext``. Dual-LLM ``USER_CHAT``
assembles chat vs tool stacks outside this enum (see ``dual_llm_message_stacks``).
"""

from __future__ import annotations

from enum import StrEnum


class PromptLegKind(StrEnum):
    """Which LLM request leg within a turn is being composed."""

    SINGLE_LLM = "single_llm"
