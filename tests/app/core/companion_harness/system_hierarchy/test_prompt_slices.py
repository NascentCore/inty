from __future__ import annotations

from app.core.companion_harness.system_hierarchy.prompt_slices import (
    PROMPT_SLICE_TO_REL,
    PromptSliceId,
    parse_persistable_prompt_slice_id,
    persistable_slice_names_csv,
    slice_to_workspace_rel,
)


def test_channels_is_persistable_prompt_slice() -> None:
    assert slice_to_workspace_rel(PromptSliceId.CHANNELS) == "CHANNELS.md"
    assert PROMPT_SLICE_TO_REL[PromptSliceId.CHANNELS] == "CHANNELS.md"
    assert parse_persistable_prompt_slice_id("channels") == PromptSliceId.CHANNELS
    assert "CHANNELS" in persistable_slice_names_csv().split(", ")
