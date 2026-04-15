"""Prompt slice ids (filename stem, no .md) for system injection and companion_update_prompt_slice."""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class PromptSliceId(StrEnum):
    """Template / workspace slice names. AGENTS is intentionally absent (legacy)."""

    BOOTSTRAP = "BOOTSTRAP"
    IDENTITY = "IDENTITY"
    SOUL = "SOUL"
    USER = "USER"
    MEMORY = "MEMORY"
    TOOLS = "TOOLS"
    HEARTBEAT = "HEARTBEAT"
    CAPABILITIES = "CAPABILITIES"


# Joins legacy single-string system prompt and interactive-bootstrap block strings.
SYSTEM_PROMPT_SLICE_SEPARATOR: Final[str] = "\n\n---\n\n"


def slice_to_workspace_rel(slice_id: PromptSliceId) -> str | None:
    """Workspace-relative path for persisted slices; BOOTSTRAP is package-only."""
    if slice_id == PromptSliceId.BOOTSTRAP:
        return None
    return f"{slice_id.value}.md"


_PERSISTABLE_SLICE_IDS: Final[frozenset[PromptSliceId]] = frozenset(
    {
        PromptSliceId.IDENTITY,
        PromptSliceId.SOUL,
        PromptSliceId.USER,
        PromptSliceId.MEMORY,
        PromptSliceId.TOOLS,
        PromptSliceId.HEARTBEAT,
        PromptSliceId.CAPABILITIES,
    }
)


def _persistable_workspace_rel(slice_id: PromptSliceId) -> str:
    rel = slice_to_workspace_rel(slice_id)
    if rel is None:
        raise RuntimeError(f"persistable slice expected workspace rel: {slice_id!r}")
    return rel


# Slices writable via companion_update_prompt_slice (not BOOTSTRAP); rel from slice_to_workspace_rel.
PROMPT_SLICE_TO_REL: Final[dict[PromptSliceId, str]] = {
    sid: _persistable_workspace_rel(sid)
    for sid in sorted(_PERSISTABLE_SLICE_IDS, key=lambda s: s.value)
}


def parse_persistable_prompt_slice_id(raw: str) -> PromptSliceId | None:
    key = (raw or "").strip().upper()
    if not key:
        return None
    try:
        sid = PromptSliceId(key)
    except ValueError:
        return None
    return sid if sid in PROMPT_SLICE_TO_REL else None


def persistable_slice_names_csv() -> str:
    return ", ".join(sorted(s.value for s in PROMPT_SLICE_TO_REL))
