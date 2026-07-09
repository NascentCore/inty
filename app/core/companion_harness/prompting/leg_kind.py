"""LLM request leg identity within a companion turn (dual-LLM vs single-LLM).

Phase 1 only uses ``SINGLE_LLM``. ``CHAT_LEG`` and ``TOOL_LEG`` activate in Phase 2
when ``USER_CHAT`` dual-LLM paths move to ``TrackSystemRecipe`` (#3453).
"""

from __future__ import annotations

from enum import StrEnum


class PromptLegKind(StrEnum):
    """Which LLM request leg within a turn is being composed."""

    SINGLE_LLM = "single_llm"
    CHAT_LEG = "chat_leg"
    TOOL_LEG = "tool_leg"
