"""Prompt slice ids: runtime system-injection units mapped from Memory docs or package seeds.

**Memory doc** = persistency (MemoryStore / Postgres). Human-readable markdown for
examination and LLM tool I/O.

**Prompt slice** = runtime effect (assembled ``role: system`` blocks per turn).
Persistable slices are **1:1** with a workspace-relative ``{STEM}.md`` Memory doc
(``slice_to_workspace_rel``). Slices may also come from package templates only
(``BOOTSTRAP``, ``TOOLS``) or from Python-assembled text (doctrine, channel format,
user-time tail) with **no** Memory doc.

``PromptSliceId.MEMORY`` → ``MEMORY.md``. Daily gist: ``memory/daily/<date>.md``
(dreaming-written); see ``memory_taxonomy``.

TODO(companion-package-reorg): Move this module into a focused sub-package under companion_harness (see issue body for draft layout).
https://github.com/NascentCore/inty/issues/3409
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class PromptSliceId(StrEnum):
    """Workspace slice ids for persisted markdown paths used in system injection.

    ``BOOTSTRAP`` is package-only (no workspace path). ``TOOLS`` / ``SIGNIFICANCE_PERCEPTION`` are
    fixed from package templates for model injection, not store-backed prompt slices.
    ``CHANNELS`` is persistable and injected through ``PromptBundle.channels_md``.
    ``COMPANIONSHIP`` is persistable; injected post-bootstrap in ``_persona_system_messages``.
    """

    BOOTSTRAP = "BOOTSTRAP"
    SOUL = "SOUL"
    STYLE = "STYLE"
    IDENTITY = "IDENTITY"
    USER = "USER"
    MEMORY = "MEMORY"
    CHANNELS = "CHANNELS"
    COMPANIONSHIP = "COMPANIONSHIP"


def slice_to_workspace_rel(slice_id: PromptSliceId) -> str | None:
    """Workspace-relative path for persisted slices; BOOTSTRAP is package-only."""
    if slice_id == PromptSliceId.BOOTSTRAP:
        return None
    return f"{slice_id.value}.md"


# TODO(prompt-slice-dedup): Canonical persistable slices; memory_store_scope seeding should derive from here. #3417
_PERSISTABLE_SLICE_IDS: Final[frozenset[PromptSliceId]] = frozenset(
    {
        PromptSliceId.IDENTITY,
        PromptSliceId.SOUL,
        PromptSliceId.STYLE,
        PromptSliceId.USER,
        PromptSliceId.MEMORY,
        PromptSliceId.CHANNELS,
        PromptSliceId.COMPANIONSHIP,
    }
)


def _persistable_workspace_rel(slice_id: PromptSliceId) -> str:
    rel = slice_to_workspace_rel(slice_id)
    if rel is None:
        raise RuntimeError(
            f"persistable slice expected workspace rel: {slice_id!r}"
        )
    return rel


PROMPT_SLICE_TO_REL: Final[dict[PromptSliceId, str]] = {
    sid: _persistable_workspace_rel(sid)
    for sid in sorted(_PERSISTABLE_SLICE_IDS, key=lambda s: s.value)
}
