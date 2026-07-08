"""Stability-first ordering for projected MemDoc slices (KV-cache prefix reuse).

Target ordering invariant: most durable slices at the head, most volatile at the tail.
Importance sorts only within a stability band:

    effective_order = (slot_rank, stability_band, relevance × priority × decay)

``relevance`` is the retrieval term; resident slices pin relevance to 1.

**Today**: no score-based sort — assembly order is fixed in ``PromptBuilder`` / ``tracks``.

TODO(#3521): Score-based ordering deferred — ``compute_effective_order`` and stability-band
sort are not material at current scale; implement when memory projection pipeline lands.

TODO(memory-projection-pipeline): Implement ``compute_effective_order`` when selection — #3521
stage lands (#3521).
"""

from __future__ import annotations

from enum import StrEnum


class StabilityBand(StrEnum):
    """Abstraction / volatility band for KV-cache-friendly prompt prefix ordering."""

    DURABLE = "durable"
    SESSION = "session"
    EPHEMERAL = "ephemeral"
