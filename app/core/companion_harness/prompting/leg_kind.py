"""LLM request leg identity within a companion turn.

Phase 1 composes a single OpenAI completion per track via ``SINGLE_LLM``.
Additional leg kinds belong in ``TrackSystemRecipe`` when dual-LLM lands (#3453).
"""

from __future__ import annotations

from enum import StrEnum


class PromptLegKind(StrEnum):
    """Which LLM request leg within a turn is being composed."""

    SINGLE_LLM = "single_llm"
