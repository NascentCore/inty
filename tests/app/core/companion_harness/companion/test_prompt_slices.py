from __future__ import annotations

from app.core.companion_harness.companion.prompt_slices import (
    PROMPT_SLICE_TO_REL,
    PromptSliceId,
    slice_to_workspace_rel,
)


def test_channels_maps_to_workspace_rel() -> None:
    assert slice_to_workspace_rel(PromptSliceId.CHANNELS) == "CHANNELS.md"
    assert PROMPT_SLICE_TO_REL[PromptSliceId.CHANNELS] == "CHANNELS.md"
