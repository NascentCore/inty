"""Code-owned global slot order for memory projection (safety/determinism boundary).

Target design: harness keeps a small ``slot → rank`` table; intra-slot inclusion and
order are metadata-driven (``MemDocFrontmatter``). The agent never reorders structural
slots. Adding a new slot category is a one-line rank entry; new docs need no code change
once slot membership lives in data (#3549).

**Today**: ranks mirror hardcoded ``PromptBuilder`` / ``tracks`` assembly order using
scope-relative paths as stand-ins until slot model lands (#3453).

TODO(#3521): Score-based ordering (slot rank + stability band) deferred — prompt order
not material at current scale; keep fixed assembly order until #3521 lands.

TODO(track-driven-system-messages-building): Replace path keys with slot ids when — #3453
further named-slot templates migrate remaining imperative assembly.
"""

from __future__ import annotations

from typing import Final

from app.core.companion_harness.memory.memory_store_scope import (
    DEFAULT_MEMORY_STORE_SCOPE_PATHS,
)

_PATHS = DEFAULT_MEMORY_STORE_SCOPE_PATHS

# Lower rank = earlier in prompt prefix (more cache-stable / durable).
SLOT_RANK: Final[dict[str, int]] = {
    _PATHS.identity: 10,
    _PATHS.soul: 20,
    _PATHS.user_md: 30,
    _PATHS.style_md: 40,
    _PATHS.companionship_md: 50,
    _PATHS.memory_md: 60,
    _PATHS.living_sphere_md: 70,
    _PATHS.techno_core_md: 80,
}
