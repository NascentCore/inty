from __future__ import annotations

import re
from dataclasses import dataclass

_PREFERRED_PATTERNS = (
    re.compile(r"(?:以后)?(?:请)?叫我([A-Za-z\u4e00-\u9fff]{1,16})"),
    re.compile(r"(?:以后)?(?:请)?称呼我([A-Za-z\u4e00-\u9fff]{1,16})"),
    re.compile(r"我(?:更)?喜欢你叫我([A-Za-z\u4e00-\u9fff]{1,16})"),
)
_CITY_RE = re.compile(r"我(?:现在)?住在([A-Za-z\u4e00-\u9fff]{1,24})")
_PET_RE = re.compile(r"我养了一只([A-Za-z\u4e00-\u9fff]{1,24})")
_DAY_RE = re.compile(r"我是周([一二三四五六日天])休息")
_COFFEE_RE = re.compile(r"(不喝咖啡|喝咖啡)")
_BOUNDARY_RE = re.compile(r"(?:请)?(?:不要|别)叫我([A-Za-z\u4e00-\u9fff]{1,16})")
_NO_COFFEE_RE = re.compile(r"(?:不|别|不要)(?:再)?喝咖啡")
_NO_PET_RE = re.compile(r"(?:不|没)(?:有)?养宠物")
_CITY_MOVE_PATTERNS = (
    re.compile(r"(?:我)?搬家了.*?现在住在([A-Za-z\u4e00-\u9fff]{1,24})"),
    re.compile(r"现在住在([A-Za-z\u4e00-\u9fff]{1,24})"),
)


@dataclass(frozen=True)
class SlotCandidate:
    key: str
    value: str
    confidence: float
    evidence: str
    turn_idx: int
    is_negative: bool = False


def extract_candidates(text: str, turn_idx: int) -> list[SlotCandidate]:
    """Extract per-turn slot candidates with confidence and evidence."""
    out: list[SlotCandidate] = []
    boundary_blocked_names: set[str] = set()
    for m in _BOUNDARY_RE.finditer(text):
        blocked = m.group(1)
        boundary_blocked_names.add(blocked)
        out.append(
            SlotCandidate(
                key="boundary",
                value=f"不要叫我{blocked}",
                confidence=0.98,
                evidence=m.group(0),
                turn_idx=turn_idx,
            )
        )

    for p in _PREFERRED_PATTERNS:
        for m in p.finditer(text):
            preferred_name = m.group(1)
            if len(preferred_name) <= 1:
                continue
            # Same-turn contradiction: boundary statement wins.
            if preferred_name in boundary_blocked_names:
                continue
            out.append(
                SlotCandidate(
                    key="preferred_name",
                    value=preferred_name,
                    confidence=0.90,
                    evidence=m.group(0),
                    turn_idx=turn_idx,
                )
            )
            break

    city = None
    for p in _CITY_MOVE_PATTERNS:
        city = p.search(text)
        if city:
            break
    if city:
        out.append(
            SlotCandidate(
                key="city",
                value=city.group(1),
                confidence=0.88,
                evidence=city.group(0),
                turn_idx=turn_idx,
            )
        )

    no_pet = _NO_PET_RE.search(text)
    if no_pet:
        out.append(
            SlotCandidate(
                key="pet",
                value="无",
                confidence=0.92,
                evidence=no_pet.group(0),
                turn_idx=turn_idx,
                is_negative=True,
            )
        )
    pet = _PET_RE.search(text)
    if pet and not no_pet:
        out.append(
            SlotCandidate(
                key="pet",
                value=pet.group(1),
                confidence=0.86,
                evidence=pet.group(0),
                turn_idx=turn_idx,
            )
        )

    day = _DAY_RE.search(text)
    if day:
        out.append(
            SlotCandidate(
                key="rest_day",
                value=f"周{day.group(1)}",
                confidence=0.90,
                evidence=day.group(0),
                turn_idx=turn_idx,
            )
        )

    no_coffee = _NO_COFFEE_RE.search(text)
    if no_coffee:
        out.append(
            SlotCandidate(
                key="coffee_preference",
                value="不喝咖啡",
                confidence=0.94,
                evidence=no_coffee.group(0),
                turn_idx=turn_idx,
                is_negative=True,
            )
        )
    coffee = _COFFEE_RE.search(text)
    if coffee and not no_coffee:
        out.append(
            SlotCandidate(
                key="coffee_preference",
                value=coffee.group(1),
                confidence=0.85,
                evidence=coffee.group(0),
                turn_idx=turn_idx,
            )
        )

    return out


def extract_memory_facts(text: str) -> dict[str, str]:
    """
    Compatibility helper used by baseline agent:
    direct text parse to key-value facts.
    """
    facts: dict[str, str] = {}
    for c in extract_candidates(text, turn_idx=0):
        facts[c.key] = c.value
    return facts


def is_more_reliable_name_candidate(new: SlotCandidate, old: SlotCandidate) -> bool:
    """Reliability rule for preferred-name candidate overwrite."""
    if new.is_negative and not old.is_negative:
        return False
    if old.is_negative and not new.is_negative:
        return True
    if new.turn_idx > old.turn_idx:
        return True
    if new.turn_idx < old.turn_idx:
        return False
    if new.confidence > old.confidence:
        return True
    if new.confidence < old.confidence:
        return False
    return len(new.evidence) > len(old.evidence)


def is_invalid_preferred_name_against_boundary(
    preferred_name: str, boundary_text: str | None
) -> bool:
    """Check cross-slot contradiction: preferred_name blocked by boundary."""
    if not boundary_text:
        return False
    m = _BOUNDARY_RE.search(boundary_text)
    if not m:
        return False
    blocked = m.group(1)
    return preferred_name == blocked
