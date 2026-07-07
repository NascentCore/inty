"""Deterministic projection: order, budget, and render selected slices into a PromptPlan.

Generated entirely by Cursor agent.
"""

from __future__ import annotations

from collections.abc import Callable

from app.core.companion_harness.companion.models import CompanionTurnTrack
from app.core.companion_harness.memory.retrieval import SliceSelection
from app.core.companion_harness.prompt_builder import PromptPlan


def project_slices_to_prompt_plan(
    *,
    selection: SliceSelection,
    budget_tokens: int,
    track: CompanionTurnTrack,
    legacy_messages_builder: Callable[[], PromptPlan],
) -> PromptPlan:
    """Deterministic projection wrapper; today delegates to legacy builders."""
    assert selection is not None
    assert track is not None
    _ = budget_tokens
    return legacy_messages_builder()
