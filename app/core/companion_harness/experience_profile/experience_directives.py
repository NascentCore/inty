"""Real-time experience knobs persisted in companion ``context.json``.

``experience_directives.intent`` captures what companionship experience the user
wants (casual chat, deep conversation, role-play, …). The harness maps intent to
``context_mode`` (memory injection + legacy clause). ``tone`` overlays session stance.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from app.core.companion_harness.experience_profile.context_mode import (
    ExperienceContextMode,
)


class ExperienceSessionIntent(StrEnum):
    """User-facing session experience: what kind of companionship they want."""

    CASUAL_CHAT = "casual_chat"
    DEEP_CONVERSATION = "deep_conversation"
    ROLEPLAY = "roleplay"
    EMOTIONAL_SUPPORT = "emotional_support"
    REMOTE_ROMANCE = "remote_romance"
    INTERACTIVE_FICTION = "interactive_fiction"


def context_mode_for_session_intent(intent: ExperienceSessionIntent) -> str:
    """Map user session intent to harness ``context_mode`` (memory + base clause)."""

    match intent:
        case ExperienceSessionIntent.CASUAL_CHAT:
            return ExperienceContextMode.EMOTIONAL_COMPANION.value
        case ExperienceSessionIntent.DEEP_CONVERSATION:
            return ExperienceContextMode.INTIMATE.value
        case ExperienceSessionIntent.ROLEPLAY:
            return ExperienceContextMode.ROLEPLAY.value
        case ExperienceSessionIntent.EMOTIONAL_SUPPORT:
            return ExperienceContextMode.EMOTIONAL_COMPANION.value
        case ExperienceSessionIntent.REMOTE_ROMANCE:
            return ExperienceContextMode.REMOTE_LOVER.value
        case ExperienceSessionIntent.INTERACTIVE_FICTION:
            return ExperienceContextMode.INTERACTIVE_FICTION.value


class ExperienceDirectiveTone(StrEnum):
    """Interaction stance overlay; complements ``context_mode`` system clause."""

    WARM = "warm"
    PLAYFUL = "playful"
    COOL = "cool"
    DIRECT = "direct"


class ExperienceDirectives(BaseModel):
    """Fast session experience directives; never updated by dreaming."""

    intent: ExperienceSessionIntent | None = Field(
        default=None,
        description=(
            "What companionship experience the user wants (casual chat, deep conversation, "
            "role-play, etc.). Mapped to harness context_mode on persist."
        ),
    )
    tone: ExperienceDirectiveTone | None = Field(
        default=None,
        description=(
            "Optional tone overlay (warm / playful / cool / direct). "
            "Unset until user/tool sets via bootstrap or profile tools (#3343)."
        ),
    )

    @field_validator("intent", mode="before")
    @classmethod
    def _normalize_intent(cls, v: object) -> object:
        if v is None or v == "":
            return None
        if isinstance(v, ExperienceSessionIntent):
            return v
        if isinstance(v, str):
            normalized = v.strip().lower()
            if not normalized:
                return None
            return ExperienceSessionIntent(normalized)
        return v

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

_INTENT_CLAUSE_BODY: dict[ExperienceSessionIntent, str] = {
    ExperienceSessionIntent.CASUAL_CHAT: "轻松闲聊为主，不必每轮都挖深层话题。",
    ExperienceSessionIntent.DEEP_CONVERSATION: "偏深度对话与共情，可追问与延展，但仍尊重节奏。",
    ExperienceSessionIntent.ROLEPLAY: "角色扮演与场景延续优先，保持 IC 一致。",
    ExperienceSessionIntent.EMOTIONAL_SUPPORT: "情感陪伴与共情优先，避免戏剧化套路。",
    ExperienceSessionIntent.REMOTE_ROMANCE: "异地亲密体感：时差、想念、见面期待与口语化互动。",
    ExperienceSessionIntent.INTERACTIVE_FICTION: "互动小说/叙事推进优先，将用户输入视为行动或选择。",
}


def experience_directives_system_clause(
    directives: ExperienceDirectives,
) -> str | None:
    """Build overlay clause when ``experience_directives`` has active knobs; else None."""

    lines: list[str] = []
    if directives.intent is not None:
        lines.append(
            f"用户想要的相处体验：`{directives.intent.value}`。"
            f"{_INTENT_CLAUSE_BODY[directives.intent]}"
        )
    if directives.tone is not None:
        lines.append(
            f"语气细调：`{directives.tone.value}`。{_TONE_CLAUSE_BODY[directives.tone]}"
        )
    if not lines:
        return None
    body = "\n".join(lines)
    return (
        f"{EXPERIENCE_DIRECTIVES_SYSTEM_HEADING}{body}\n"
        "长期 bond 见 COMPANIONSHIP.md；harness `context_mode` 由 intent 映射，勿向用户解释内部字段名。"
    )
