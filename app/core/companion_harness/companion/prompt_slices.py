"""Prompt slice ids (filename stem, no .md) for system injection and companion_update_prompt_slice.

``PromptSliceId.MEMORY`` maps to ``MEMORY.md`` (semantic memory). Episodic and gist layers live under
``memory/daily/<date>.md`` and ``memory/<date>.md`` instead; see ``memory_taxonomy``.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class PromptSliceId(StrEnum):
    """Persistable workspace slices updatable via ``companion_update_prompt_slice``.

    ``BOOTSTRAP`` is package-only (no workspace path). ``TOOLS`` / ``SIGNIFICANCE_PERCEPTION`` are
    fixed from package templates for model injection, not store-backed prompt slices.
    """

    BOOTSTRAP = "BOOTSTRAP"
    SOUL = "SOUL"
    STYLE = "STYLE"
    IDENTITY = "IDENTITY"
    USER = "USER"
    MEMORY = "MEMORY"


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
        PromptSliceId.STYLE,
        PromptSliceId.USER,
        PromptSliceId.MEMORY,
    }
)


def _persistable_workspace_rel(slice_id: PromptSliceId) -> str:
    rel = slice_to_workspace_rel(slice_id)
    if rel is None:
        raise RuntimeError(
            f"persistable slice expected workspace rel: {slice_id!r}"
        )
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
