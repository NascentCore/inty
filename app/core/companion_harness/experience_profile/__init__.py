"""Experience profile ids live in companion ``context.json`` as ``context_mode``.

Maps product-facing experience ids to system-clause text and private-memory injection
rules used when assembling companion system messages.
"""

from app.core.companion_harness.experience_profile.context_mode import (
    EXPERIENCE_PROFILE_CONTEXT_MODE_HEADING,
    EXPERIENCE_PROFILE_ID_BOOTSTRAP,
    ExperienceContextMode,
    experience_profile_injects_private_memory,
    experience_profile_system_clause,
    normalize_experience_profile_id,
)

__all__ = [
    "EXPERIENCE_PROFILE_CONTEXT_MODE_HEADING",
    "EXPERIENCE_PROFILE_ID_BOOTSTRAP",
    "ExperienceContextMode",
    "experience_profile_injects_private_memory",
    "experience_profile_system_clause",
    "normalize_experience_profile_id",
]
