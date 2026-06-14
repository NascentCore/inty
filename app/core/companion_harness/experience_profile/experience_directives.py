"""Real-time experience knobs persisted in companion ``context.json``.

``context_mode`` is the coarse product switch; ``experience_directives`` holds
session-level overlays (tone, pacing) that refine the active experience profile.
Phase A (#3342): schema + load/save only — prompt clause in Phase B (#3343).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class ExperienceDirectiveTone(StrEnum):
    """Interaction stance overlay; complements ``context_mode`` system clause."""

    WARM = "warm"
    PLAYFUL = "playful"
    COOL = "cool"
    DIRECT = "direct"


class ExperienceDirectives(BaseModel):
    """Fast session experience directives; never updated by dreaming."""

    tone: ExperienceDirectiveTone | None = Field(
        default=None,
        description=(
            "Optional tone overlay (warm / playful / cool / direct). "
            "Unset until user/tool sets via bootstrap or profile tools (#3343)."
        ),
    )

    @field_validator("tone", mode="before")
    @classmethod
    def _normalize_tone(cls, v: object) -> object:
        if v is None or v == "":
            return None
        if isinstance(v, ExperienceDirectiveTone):
            return v
        if isinstance(v, str):
            normalized = v.strip().lower()
            if not normalized:
                return None
            return ExperienceDirectiveTone(normalized)
        return v
