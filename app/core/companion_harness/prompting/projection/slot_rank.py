"""Code-owned global slot order for memory projection (safety/determinism boundary).

Target design: harness keeps a small ``slot → rank`` table; intra-slot inclusion and
order are metadata-driven (``MemDocFrontmatter``). The agent never reorders structural
slots. Adding a new slot category is a one-line rank entry; new docs need no code change
once slot membership lives in data (#3549).

**Today**: ranks mirror hardcoded ``PromptBuilder`` / ``tracks`` assembly order using
scope-relative paths as stand-ins until slot model lands (#3453).

TODO(track-driven-system-messages-building): Replace path keys with slot ids when — #3453
PromptTemplate / named-slot assembly lands.
"""

from __future__ import annotations

from typing import Final

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

# Lower rank = earlier in prompt prefix (more cache-stable / durable).
SLOT_RANK: Final[dict[str, int]] = {
    IDENTITY_MD_REL: 10,
    SOUL_MD_REL: 20,
    USER_MD_REL: 30,
    STYLE_MD_REL: 40,
    COMPANIONSHIP_MD_REL: 50,
    MEMORY_MD_REL: 60,
    LIVING_SPHERE_MD_REL: 70,
    TECHNO_CORE_MD_REL: 80,
}
