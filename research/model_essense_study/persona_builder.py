from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from random import Random
from typing import Iterable

from loguru import logger

from research.model_essense_study.schema import AgentPersonaRaw, PersonaRecord


@dataclass(frozen=True)
class PersonaSelectionResult:
    items: list[PersonaRecord]
    coverage_summary: dict[str, int]


def _normalize_gender(gender: str | None) -> str:
    if not gender:
        return "OTHER"
    normalized = gender.strip().upper()
    if normalized in {"MALE", "FEMALE", "OTHER"}:
        return normalized
    return "OTHER"


def _infer_age_band(text: str) -> str:
    lowered = text.lower()
    if "18" in lowered or "college" in lowered or "student" in lowered:
        return "18-24"
    if "young professional" in lowered or "mid-20" in lowered:
        return "25-29"
    if "30" in lowered:
        return "30-34"
    return "35+"


def _infer_cluster(text: str) -> str:
    rules: list[tuple[str, tuple[str, ...]]] = [
        ("gentle", ("gentle", "kind", "warm", "supportive", "caring")),
        ("playful", ("playful", "fun", "tease", "flirty", "cheerful")),
        ("rational", ("logic", "calm", "analytic", "structured", "reason")),
        ("assertive", ("dominant", "assertive", "bold", "possessive", "mysterious")),
    ]
    for label, keywords in rules:
        if any(k in text for k in keywords):
            return label
    return "balanced"


def select_personas(
    *, candidates: Iterable[AgentPersonaRaw], target_count: int
) -> PersonaSelectionResult:
    pool = list(candidates)
    grouped: dict[tuple[str, str, str], list[PersonaRecord]] = defaultdict(list)
    for item in pool:
        text = " ".join(
            [
                item.name,
                item.personality or "",
                item.scenario or "",
                " ".join(item.tags),
            ]
        ).strip()
        normalized = PersonaRecord(
            persona_id=f"persona-{item.agent_id}",
            source_agent_id=item.agent_id,
            source_agent_name=item.name,
            gender=_normalize_gender(item.gender),
            age_band=_infer_age_band(text),
            personality_cluster=_infer_cluster(text),
            personality_text=item.personality or "",
            scenario_text=item.scenario or "",
            tags=item.tags,
        )
        grouped[
            (
                normalized.gender,
                normalized.age_band,
                normalized.personality_cluster,
            )
        ].append(normalized)

    rng = Random(42)
    keys = sorted(grouped.keys())
    for key in keys:
        rng.shuffle(grouped[key])

    selected: list[PersonaRecord] = []
    cursor = 0
    while len(selected) < target_count and keys:
        key = keys[cursor % len(keys)]
        bucket = grouped[key]
        if bucket:
            selected.append(bucket.pop())
        cursor += 1
        if all(not bucket_items for bucket_items in grouped.values()):
            break

    summary: dict[str, int] = defaultdict(int)
    for item in selected:
        summary[f"gender:{item.gender}"] += 1
        summary[f"age_band:{item.age_band}"] += 1
        summary[f"cluster:{item.personality_cluster}"] += 1

    logger.info(
        "Selected personas {} / target {}",
        len(selected),
        target_count,
    )
    logger.debug(
        "Persona sample preview: {}",
        [persona.model_dump(mode="json") for persona in selected[:3]],
    )
    return PersonaSelectionResult(items=selected, coverage_summary=dict(summary))
