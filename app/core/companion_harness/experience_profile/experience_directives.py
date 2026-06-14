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


EXPERIENCE_DIRECTIVES_SYSTEM_HEADING = (
    "EXPERIENCE DIRECTIVES — 本会话体验细调（context.json experience_directives）\n\n"
)

_TONE_CLAUSE_BODY: dict[ExperienceDirectiveTone, str] = {
    ExperienceDirectiveTone.WARM: "语气偏温暖、接纳，可适度表达关心。",
    ExperienceDirectiveTone.PLAYFUL: "语气偏轻松俏皮，可适度玩笑，仍尊重边界。",
    ExperienceDirectiveTone.COOL: "语气偏克制、冷静，减少过度热情或黏人表达。",
    ExperienceDirectiveTone.DIRECT: "语气偏直接坦率，少绕弯，仍保持尊重。",
}


def experience_directives_system_clause(
    directives: ExperienceDirectives,
) -> str | None:
    """Build overlay clause when ``experience_directives`` has active knobs; else None."""

    if directives.tone is None:
        return None
    body = _TONE_CLAUSE_BODY[directives.tone]
    return (
        f"{EXPERIENCE_DIRECTIVES_SYSTEM_HEADING}"
        f"当前 tone 细调：`{directives.tone.value}`。{body}\n"
        "在 `context_mode` 粗开关之上调节本会话互动体感；长期 bond 见 COMPANIONSHIP.md。"
    )
