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

_scope_paths = DEFAULT_MEMORY_STORE_SCOPE_PATHS

# Lower rank = earlier in prompt prefix (more cache-stable / durable).
SLOT_RANK: Final[dict[str, int]] = {
    _scope_paths.identity: 10,
    _scope_paths.soul: 20,
    _scope_paths.user_md: 30,
    _scope_paths.style_md: 40,
    _scope_paths.companionship_md: 50,
    _scope_paths.memory_md: 60,
    _scope_paths.living_sphere_md: 70,
    _scope_paths.techno_core_md: 80,
}
