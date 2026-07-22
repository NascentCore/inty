"""Retrieval / selection stage: which MemoryStore slices are candidates this turn.

MemoryStore remains the single source of truth. Target tiers mirror human memory:

- **Resident** — always candidate (doctrine seeds, identity/persona core, control state).
- **Verbatim window** — recent turns as exact messages; anchored to dreaming cycle (~one day)
  with token budget as hard cap (#3376).
- **Associative** — older/larger material fetched on demand by relevance.

Retrieval stance (target): structured navigation over slot tree + lexical search over
markdown first; optional local semantic index as derived candidate generator that re-reads
canonical MemDoc; external memory services off by default.

**Today**: eager ``load_prompt_bundle`` reads fixed paths; transcript window via
``turn_pipeline``; ``transcript_compaction`` is an associative-tier prototype (#3523).

**AwakeTurn invariant**: selection reads only — no MemDoc curation during awake turns.

TODO(#3775): Offline fork-at-turn + structural diff over projected
slices for CRS counterfactual eval (shared-prefix replay from cache) — #3775 (epic #3341).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.core.companion_harness.companion.models import CompanionTurnTrack
from app.core.companion_harness.memory.memory_store import MemoryStore
from app.core.companion_harness.memory.memory_store_path_constants import (
    CHAT_HISTORY_MD_REL,
)
from app.core.companion_harness.prompting.bundle import PromptBundle


class RetrievalTier(StrEnum):
    """Human-memory tier for slice candidacy this turn."""

    RESIDENT = "resident"
    VERBATIM = "verbatim"
    ASSOCIATIVE = "associative"


@dataclass(frozen=True)
class SliceSelection:
    """Resident MemDoc rel paths + transcript window spec for one turn."""

    resident_paths: tuple[str, ...]
    transcript_window_spec: str


def select_slices_for_turn(
    *,
    track: CompanionTurnTrack,
    store: MemoryStore,
    bundle: PromptBundle,
) -> SliceSelection:
    """Tiered selection wrapper over today's eager ``load_prompt_bundle`` paths."""
    assert store is not None
    assert bundle is not None
    _ = track
    return SliceSelection(
        resident_paths=(),
        transcript_window_spec=CHAT_HISTORY_MD_REL,
    )
