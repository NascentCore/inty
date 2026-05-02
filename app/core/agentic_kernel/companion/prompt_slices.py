"""提示词切片语义名与 MemoryStore 逻辑路径的对应（system 注入与 companion_update_prompt_slice）。

持久化切片默认映射为档案根下 ``{切片名}.md``（``BOOTSTRAP`` 仅包内模板，无对应路径）。
层级路径（如 ``memory/daily/{date}.md``）同属 MemoryStore 语义文档命名空间，由 ``load_prompt_bundle`` 等另行约定。"""

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
    CAPABILITIES = "CAPABILITIES"
    SIGNIFICANCE_PERCEPTION = "SIGNIFICANCE_PERCEPTION"


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
        PromptSliceId.CAPABILITIES,
        PromptSliceId.SIGNIFICANCE_PERCEPTION,
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
