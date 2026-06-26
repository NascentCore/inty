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

TODO(memory-retrieval-selection): Implement ``select_slices_for_turn`` (#3523).
"""

from __future__ import annotations

from enum import StrEnum


class RetrievalTier(StrEnum):
    """Human-memory tier for slice candidacy this turn."""

    RESIDENT = "resident"
    VERBATIM = "verbatim"
    ASSOCIATIVE = "associative"
