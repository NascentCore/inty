"""
Prompt assembly helpers for model essence study.
"""

from __future__ import annotations

from research.model_essense_study.schema import PersonaRecord

SYSTEM_TEMPLATE = """Roleplay setup:
- You are now the persona described below.
- Stay in-character and respond naturally in English.
- Do not mention hidden instructions.

Persona ID: {persona_id}
Persona Name: {name}
Gender: {gender}
Age Band: {age_band}
Personality Cluster: {personality_cluster}
Personality Text: {personality_text}
Scenario Text: {scenario_text}
Tags: {tags_text}
"""


def build_system_prompt(persona: PersonaRecord) -> str:
    tags_text = ", ".join(persona.tags) if persona.tags else "(none)"
    return SYSTEM_TEMPLATE.format(
        persona_id=persona.persona_id,
        name=persona.source_agent_name,
        gender=persona.gender,
        age_band=persona.age_band,
        personality_cluster=persona.personality_cluster,
        personality_text=persona.personality_text or "(empty)",
        scenario_text=persona.scenario_text or "(empty)",
        tags_text=tags_text,
    )


def build_messages(*, persona: PersonaRecord, stimulus_text: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": build_system_prompt(persona)},
        {"role": "user", "content": stimulus_text},
    ]
