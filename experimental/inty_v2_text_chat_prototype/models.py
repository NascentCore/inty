"""Re-export from kernel companion.models + prototype-compatible load_prompt_bundle."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from app.core.agentic_kernel.companion.models import (  # noqa: F401
    TRANSCRIPT_WINDOW_MAX_MESSAGES,
    ChatMessage,
    ContextMeta,
    PromptBundle,
    load_context_meta,
    load_transcript,
    transcript_for_llm_turn,
)
from app.core.agentic_kernel.companion.models import (
    load_prompt_bundle as _kernel_load_prompt_bundle,
)

if TYPE_CHECKING:
    from app.core.agentic_kernel.companion.workspace import WorkspacePaths


def load_prompt_bundle(
    paths: WorkspacePaths,
    *,
    meta: ContextMeta | None = None,
) -> PromptBundle:
    """Prototype-compatible wrapper: auto-creates MemoryStore from registry."""
    from .memory_store_registry import get_memory_store

    store = get_memory_store(paths.root)
    return _kernel_load_prompt_bundle(paths, store, meta=meta)
