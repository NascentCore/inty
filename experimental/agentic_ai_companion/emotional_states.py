# 通用情感状态，用于陪伴/对话上下文（如状态标注、提示词）。
# app/ 中无等价物；相关概念见 app/core/prompting/verbals.VerbalCategory 与 traits。

from __future__ import annotations

from enum import Enum
from typing import NamedTuple


class EmotionalStateItem(NamedTuple):
    """Single emotional state: identifier (name) and extended description."""

    name: str
    description: str


class EmotionalState(EmotionalStateItem, Enum):
    """
    General emotional states as objects: each member has .id (string identifier) and .description.
    Use str(state), state.id, or state.value.name for the id; state.description for the extended text.
    """

    NEUTRAL = ("neutral", "No strong emotion; calm, even, or unengaged.")
    HAPPY = ("happy", "Pleased or satisfied; general positive mood.")
    JOYFUL = ("joyful", "Full of joy; elated, delighted.")
    EXCITED = (
        "excited",
        "Eager, energized; looking forward to something or stirred by the moment.",
    )
    TENDER = ("tender", "Gentle, soft, caring; emotionally warm and delicate.")
    AFFECTIONATE = (
        "affectionate",
        "Showing fondness or love; warm and loving.",
    )
    PLAYFUL = ("playful", "Light-hearted, teasing, or fun; not serious.")
    FLIRTATIOUS = (
        "flirtatious",
        "Playfully romantic or suggestive; showing attraction or interest.",
    )
    CONTENT = ("content", "Satisfied with the current situation; at ease.")
    CURIOUS = ("curious", "Wanting to know or explore more; interested.")
    SURPRISED = (
        "surprised",
        "Taken aback by something unexpected; startled or amazed.",
    )
    SAD = ("sad", "Unhappy, down, or grieving; low mood.")
    ANXIOUS = ("anxious", "Worried, nervous, or uneasy about something.")
    ANGRY = ("angry", "Strong displeasure or irritation; mad.")
    FRUSTRATED = (
        "frustrated",
        "Blocked or thwarted; annoyed that things are not going as desired.",
    )
    BORED = ("bored", "Uninterested or lacking stimulation; listless.")
    CONFUSED = ("confused", "Uncertain or unable to make sense of something.")
    NOSTALGIC = ("nostalgic", "Thinking fondly about the past; wistful.")
    HOPEFUL = ("hopeful", "Expecting something good; optimistic.")
    RELIEVED = (
        "relieved",
        "Freed from worry or tension; at ease after a concern is resolved.",
    )
    GUILTY = ("guilty", "Feeling responsible for a wrong or mistake.")
    ASHAMED = (
        "ashamed",
        "Embarrassed or disgraced by one's own actions or situation.",
    )
    DISGUSTED = ("disgusted", "Strong revulsion or distaste.")
    FEARFUL = ("fearful", "Afraid or scared; feeling threat or danger.")
    JEALOUS = (
        "jealous",
        "Resentful of someone else's advantage or relationship.",
    )
    LONELY = ("lonely", "Feeling alone or lacking connection.")
    STRESSED = ("stressed", "Under mental or emotional pressure; strained.")
    PEACEFUL = ("peaceful", "Calm and free from disturbance; serene.")
    GRATEFUL = ("grateful", "Thankful; appreciative of something or someone.")
    PROUD = (
        "proud",
        "Pleased with oneself or someone else; satisfied with an achievement.",
    )
    EMBARRASSED = (
        "embarrassed",
        "Self-conscious or awkward due to a social or personal slip.",
    )
    AROUSED = ("aroused", "Sexually or emotionally aroused; stimulated.")

    def __str__(self) -> str:
        return self.value.name

    # Enum's .name is the member name (e.g. "HAPPY"); the id string is .value.name.
    @property
    def id(self) -> str:
        """Identifier string for this state (e.g. 'happy'). Same as str(self)."""
        return self.value.name

    @property
    def description(self) -> str:
        """Extended description for this emotional state."""
        return self.value.description
