"""Experience profile ids live in companion ``context.json`` as ``context_mode``.

Maps product-facing experience ids to system-clause text and private-memory injection
rules used when assembling companion system messages.
"""

from app.core.companion_harness.experience_profile.context_mode import (
    EXPERIENCE_PROFILE_CONTEXT_MODE_HEADING,
    ExperienceContextMode,
    experience_profile_injects_private_memory,
    experience_profile_system_clause,
    normalize_experience_profile_id,
)
from app.core.companion_harness.experience_profile.experience_directives import (
    EXPERIENCE_DIRECTIVES_SYSTEM_HEADING,
    ExperienceDirectiveTone,
    ExperienceDirectives,
    experience_directives_system_clause,
)

__all__ = [
    "EXPERIENCE_DIRECTIVES_SYSTEM_HEADING",
    "EXPERIENCE_PROFILE_CONTEXT_MODE_HEADING",
    "ExperienceContextMode",
    "ExperienceDirectiveTone",
    "ExperienceDirectives",
    "experience_directives_system_clause",
    "experience_profile_injects_private_memory",
    "experience_profile_system_clause",
    "normalize_experience_profile_id",
]
