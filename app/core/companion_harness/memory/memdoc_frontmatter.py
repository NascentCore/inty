"""YAML frontmatter metadata schema for projected MemDocs.

Target: each MemDoc may carry a YAML block at the top of the markdown body. Core fields
drive projection (slot membership, within-slot priority, pin, expiry). Edited via a
dedicated ``set_doc_metadata`` op (atomic, auditable), not whole-doc rewrite (#3713).

Facet multi-membership and tagged-store facets are **out of scope** here — see #3693.

**Today**: no frontmatter parse/write; headings and paths are hardcoded in assembly code.

TODO(memdoc-frontmatter): Parse/strip frontmatter on read and wire ``set_doc_metadata`` tool. — #3713

TODO(memdoc-belief-provenance): Extend schema with structured belief claim provenance
(``created_by``, ``caused_by_event``, evidence refs) beyond ``source`` hint — #3774 (epic #3341).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MemDocFrontmatter(BaseModel):
    """Per-MemDoc projection metadata (YAML frontmatter target schema)."""

    model_config = ConfigDict(frozen=True)

    slot: str = Field(description="Slot id for global rank table lookup.")
    priority: int = Field(
        ge=0,
        le=100,
        description="Within-slot ordering weight (0–100).",
    )
    pinned: bool = Field(
        default=False,
        description="Always included; exempt from projection budget.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Omit slice from projection after this instant.",
    )
    active: bool | None = Field(
        default=None,
        description="Optional soft enable flag for situational activation.",
    )
    heading: str | None = Field(
        default=None,
        description="Injection heading override; replaces code-owned taxonomy labels.",
    )
    source: str | None = Field(
        default=None,
        description="Provenance hint (e.g. dreaming curator, user tool).",
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Last metadata mutation timestamp.",
    )
