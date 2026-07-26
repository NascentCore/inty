"""Smoke tests for memory projection design stubs (Phase 0, no runtime behavior)."""

from __future__ import annotations

from datetime import datetime, UTC

import pytest
from pydantic import ValidationError

from app.core.companion_harness.memory.memdoc_frontmatter import (
    MemDocFrontmatter,
)
from app.core.companion_harness.memory.memory_store_path_constants import (
    COMPANIONSHIP_MD_REL,
    IDENTITY_MD_REL,
    LIVING_SPHERE_MD_REL,
    MEMORY_MD_REL,
    SOUL_MD_REL,
    STYLE_MD_REL,
    TECHNO_CORE_MD_REL,
    USER_MD_REL,
)
from app.core.companion_harness.memory.retrieval import RetrievalTier
from app.core.companion_harness.prompting.projection import ordering, slot_rank
from app.core.companion_harness.prompting.projection.ordering import (
    StabilityBand,
)


def test_projection_stub_modules_import() -> None:
    assert RetrievalTier.RESIDENT.value == "resident"
    assert StabilityBand.DURABLE.value == "durable"
    assert slot_rank.SLOT_RANK
    assert ordering.StabilityBand.EPHEMERAL == StabilityBand.EPHEMERAL


def test_slot_rank_values_are_integers() -> None:
    for path, rank in slot_rank.SLOT_RANK.items():
        assert isinstance(path, str)
        assert isinstance(rank, int)


def test_slot_rank_keys_use_canonical_memdoc_path_constants() -> None:
    expected = {
        IDENTITY_MD_REL,
        SOUL_MD_REL,
        USER_MD_REL,
        STYLE_MD_REL,
        COMPANIONSHIP_MD_REL,
        MEMORY_MD_REL,
        LIVING_SPHERE_MD_REL,
        TECHNO_CORE_MD_REL,
    }
    assert set(slot_rank.SLOT_RANK) == expected


def test_memdoc_frontmatter_validates() -> None:
    meta = MemDocFrontmatter(
        slot="persona.core",
        priority=50,
        pinned=True,
        expires_at=datetime(2026, 6, 25, tzinfo=UTC),
    )
    assert meta.slot == "persona.core"
    assert meta.pinned is True


def test_memdoc_frontmatter_rejects_priority_out_of_range() -> None:
    with pytest.raises(ValidationError):
        MemDocFrontmatter(slot="x", priority=101)
