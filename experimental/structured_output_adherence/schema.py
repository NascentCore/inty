from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field


class ConversationScenario(BaseModel):
    """
    Target JSON shape for the experiment. Kept small so providers accept strict json_schema.
    """

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., max_length=200)
    one_line_summary: str = Field(..., max_length=500)
    inferred_topics: List[str] = Field(
        default_factory=list,
        description="Short noun phrases, max 10 items.",
    )
    emotional_tone: Literal[
        "warm",
        "tense",
        "playful",
        "supportive",
        "conflicted",
        "neutral",
        "other",
    ]
    contains_sensitive_content: bool
    confidence_0_1: float = Field(..., ge=0.0, le=1.0)


def response_format_json_schema_strict() -> dict:
    name = "conversation_scenario"
    schema = ConversationScenario.model_json_schema()
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "schema": schema,
            "strict": True,
        },
    }
